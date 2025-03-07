if __name__ == "__main__":
    import argparse
    import logging
    import os
    import time

    from funcs import (
        get_current_event,
        load_standings,
        net_top_players,
        top_players_by_diff,
    )

    parser = argparse.ArgumentParser(description="Get the net top players in a league.")
    parser.add_argument(
        "--log-level",
        type=str,
        required=False,
        default="INFO",
        dest="log_level",
        help="The log level.",
    )
    parser.add_argument(
        "-l",
        "--league-id",
        type=str,
        required=True,
        dest="league_id",
        help="The ID of the league.",
    )
    parser.add_argument(
        "-e",
        "--event-id",
        type=int,
        required=False,
        default=None,
        dest="event_id",
        help="The ID of the event.",
    )
    parser.add_argument(
        "-d",
        "--dest",
        type=str,
        required=False,
        default="dist",
        dest="destination",
        help="The destination folder.",
    )

    args = parser.parse_args()
    log_level = args.log_level
    league_id = args.league_id
    event_id = args.event_id
    destination = args.destination

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    logger = logging.getLogger(__name__)

    start_time = time.time()

    logger.info(f"Loading standings for league {league_id}")
    df = load_standings(league_id)
    logger.info(f"Loaded {len(df)} entries")

    df = top_players_by_diff(df)
    if event_id is None:
        event_id = get_current_event(df["entry_id"][0])

    logger.info(f"Calculating net top players for event {event_id}")
    df = net_top_players(df, event_id=event_id)

    logger.info(f"Writing top players to CSV")

    filename = f"top-players-league-{league_id}-event-{event_id}.csv"
    path = os.path.join(destination, filename)

    df.write_csv(path, separator=";", include_bom=True)

    logger.info(f"Finished in {time.time() - start_time:.2f} seconds")
