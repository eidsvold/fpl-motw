from traceback import print_exc

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from ..external.fpl_api import FantasyPremierLeagueAPI
from ..internal.motw import InvalidLeagueError, LeagueNotFoundError, ManagerOfTheWeek

router = APIRouter()
motw = ManagerOfTheWeek(fpl_api=FantasyPremierLeagueAPI())


@router.post("/report/{league_id}")
async def generate_report(league_id: str):
    try:
        filename, buffer = motw.generate_report(league_id)
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
        raise HTTPException(status_code=500, detail=str(e))
