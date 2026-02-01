"""Payment Link Service - A web app for creating x402-protected payment links."""

import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING, AsyncGenerator

from fastapi import FastAPI, Query, Request, Response
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from config import settings
from database import create_payment, get_payment, init_db, update_payment_status

# Static files directory
STATIC_DIR = Path(__file__).parent / "static"

if TYPE_CHECKING:
    from x402_payment_service import PaymentService as PaymentServiceType

try:
    from x402_payment_service import PaymentService
except ImportError:
    PaymentService = None  # type: ignore[misc, assignment]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Initialize database on startup."""
    await init_db()
    yield


app = FastAPI(
    title=settings.app_name,
    lifespan=lifespan,
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch all unhandled exceptions and return a JSON error response."""
    import traceback

    return JSONResponse(
        status_code=500,
        content={
            "error": str(exc),
            "type": type(exc).__name__,
            "traceback": traceback.format_exc(),
        },
    )


# Mount static files if directory exists
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
async def root() -> Response:
    """Serve the index.html page."""
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return JSONResponse(
        {
            "service": settings.app_name,
            "status": "running",
        }
    )


@app.get("/config")
async def get_config() -> dict[str, str | int]:
    """Return client configuration for the frontend.

    Returns:
        JSON with network, token, and chain configuration.
    """
    return {
        "network": settings.network,
        "tokenAddress": settings.token_address,
        "tokenName": settings.token_name,
        "tokenSymbol": settings.token_symbol,
        "tokenDecimals": settings.token_decimals,
        "tokenVersion": settings.token_version,
        "chainId": settings.chain_id,
        "explorerUrl": settings.explorer_url,
    }


@app.get("/create-payment-link")
async def create_payment_link(
    amount: float = Query(..., gt=0, description="Payment amount in USD"),
    receiver: str = Query(..., description="Blockchain address to receive payment"),
) -> dict[str, str]:
    """Create a new payment link with a unique ID.

    Args:
        amount: Payment amount in USD (must be greater than 0).
        receiver: Blockchain address to receive the payment.

    Returns:
        JSON with the payment link URL.
    """
    payment_id = str(uuid.uuid4())
    await create_payment(payment_id, amount, receiver)

    payment_url = f"{settings.app_base_url}/pay/{payment_id}"
    return {
        "payment_id": payment_id,
        "payment_url": payment_url,
        "amount": str(amount),
        "receiver": receiver,
    }


def create_x402_response(payment_service: "PaymentServiceType", error: str) -> Response:
    """Create an appropriate response for x402 payment required.

    Args:
        payment_service: The PaymentService instance.
        error: Error message to include.

    Returns:
        Either HTMLResponse (for browser) or JSONResponse (for API).
    """
    content, status_code = payment_service.response(error)

    # Check if response is HTML (for browser requests) or JSON (for API)
    if isinstance(content, str):
        return HTMLResponse(content=content, status_code=status_code)
    else:
        return JSONResponse(content=content, status_code=status_code)


@app.get("/pay/{payment_id}")
async def pay(payment_id: str, request: Request) -> Response:
    """Handle payment for a specific payment ID.

    This endpoint is protected by x402. If payment is already completed,
    returns the transaction details.

    Args:
        payment_id: Unique payment identifier.
        request: FastAPI request object.

    Returns:
        JSON response with payment status or 402 payment required.
    """
    # Get payment from database
    payment_record = await get_payment(payment_id)

    if not payment_record:
        return JSONResponse(
            status_code=404,
            content={"error": "Payment not found"},
        )

    # If already paid, return the transaction details
    if payment_record["status"] == "paid":
        return JSONResponse(
            content={
                "status": "paid",
                "tx": payment_record["tx_hash"],
            }
        )

    # Check if x402 is available
    if PaymentService is None:
        return JSONResponse(
            status_code=500,
            content={
                "error": (
                    "x402_payment_service not installed. "
                    "Run: uv add git+https://github.com/second-state/"
                    "x402-payment-service.git"
                )
            },
        )

    # Create payment service for x402 verification
    try:
        payment_service: PaymentServiceType = PaymentService(
            app_name=settings.app_name,
            app_logo=settings.app_logo,
            headers=dict(request.headers),
            resource_url=str(request.url),
            price=payment_record["amount"],
            description=f"Payment for order {payment_id}",
            network=settings.network,
            pay_to_address=payment_record["receiver"],
            facilitator_url=settings.facilitator_url,
            max_timeout_seconds=settings.max_timeout_seconds,
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to initialize payment service: {e}"},
        )

    # Step 1: Parse payment header
    try:
        success, payment, selected_requirements, parse_error = payment_service.parse()
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to parse payment: {e}"},
        )

    if not success or parse_error is not None:
        return create_x402_response(payment_service, parse_error or "Payment required")

    # Type narrowing: after success check, these should not be None
    if payment is None or selected_requirements is None:
        return create_x402_response(payment_service, "Invalid payment data")

    # Step 2: Verify payment
    try:
        is_valid, verify_error = await payment_service.verify(
            payment, selected_requirements, payment_id
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to verify payment: {e}"},
        )

    if not is_valid:
        return create_x402_response(
            payment_service, verify_error or "Payment verification failed"
        )

    # Step 3: Settle payment
    try:
        (
            settle_success,
            tx_hash,
            tx_network,
            settle_error,
        ) = await payment_service.settle(payment, selected_requirements, payment_id)
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to settle payment: {e}"},
        )

    if not settle_success:
        return create_x402_response(
            payment_service, settle_error or "Payment settlement failed"
        )

    # Payment successful - update database
    await update_payment_status(payment_id, "paid", tx_hash)

    return JSONResponse(
        content={
            "status": "paid",
            "tx": tx_hash,
        }
    )


@app.get("/status/{payment_id}")
async def get_payment_status(payment_id: str) -> JSONResponse:
    """Get the current status of a payment.

    Args:
        payment_id: Unique payment identifier.

    Returns:
        JSON with payment status details.
    """
    payment_record = await get_payment(payment_id)

    if not payment_record:
        return JSONResponse(
            status_code=404,
            content={"error": "Payment not found"},
        )

    is_paid = payment_record["status"] == "paid"
    return JSONResponse(
        content={
            "payment_id": payment_id,
            "amount": payment_record["amount"],
            "paid": is_paid,
            "tx": payment_record["tx_hash"],
        }
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=True,
    )
