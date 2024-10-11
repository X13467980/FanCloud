from fastapi import APIRouter

router  = APIRouter()

@router.api_route("/send", methods=["GET", "HEAD"])
async def keep_alive():
    return {"message": "APP is active"}