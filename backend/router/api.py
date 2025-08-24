from traceback import print_exc

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from ..config import settings
from ..integrations.fpl_api import FantasyPremierLeagueAPI
from ..internal.motw import InvalidLeagueError, LeagueNotFoundError, ManagerOfTheWeek

router = APIRouter()
motw = ManagerOfTheWeek(
    fpl_api=FantasyPremierLeagueAPI(base_url=settings.FPL_API_BASE_URL)
)


@router.post("/report/{league_id}")
async def generate_report(
    league_id: str,
    limit: int = Query(10),
):
    try:
        filename, buffer = motw.generate_report(league_id, limit=limit)
        return StreamingResponse(
            buffer,
            media_type="application/octet-stream",  # Forces download
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Type": "application/octet-stream",
                "Access-Control-Expose-Headers": "Content-Disposition",  # Expose header for CORS
            },
        )

    except LeagueNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except InvalidLeagueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print_exc()
        raise HTTPException(status_code=500, detail="An unexpected error occurred")
