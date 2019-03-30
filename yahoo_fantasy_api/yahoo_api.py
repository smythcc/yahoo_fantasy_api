#!/bin/python

import json

YAHOO_ENDPOINT = 'https://fantasysports.yahooapis.com/fantasy/v2'


def get(sc, uri):
    """Send an API request to the URI and return the response as JSON

    Args:
        sc - OAuth2 session context
        uri - URI of the API to call

    Return:
        JSON document of the response
    """
    response = sc.session.get("{}/{}".format(YAHOO_ENDPOINT, uri),
                              params={'format': 'json'})
    jresp = response.json()
    if "error" in jresp:
        raise RuntimeError(json.dumps(jresp))
    return jresp


def get_teams_raw(sc):
    """Return the raw JSON when requesting the logged in players teams.

    :param sc: OAuth2 session context from yahoo_oauth
    :type sc: OAuth2
    :return: JSON document of the request.
    """
    return get(sc, "users;use_login=1/games/teams")


def get_standings_raw(sc, league_id):
    """Return the raw JSON when requesting standings for a league.

    :param sc: Session context for oauth
    :type sc: OAuth2 from yahoo_oauth
    :param league_id: League ID to get the standings for
    :type league_id: str
    :return: JSON document of the request.
    """
    return get(sc, "league/{}/standings".format(league_id))


def get_settings_raw(sc, league_id):
    """Return the raw JSON when requesting settings for a league.

    :param sc: Session context for oauth
    :type sc: OAuth2 from yahoo_oauth
    :param league_id: League ID to get the standings for
    :type league_id: str
    :return: JSON document of the request.
    """
    return get(sc, "league/{}/settings".format(league_id))