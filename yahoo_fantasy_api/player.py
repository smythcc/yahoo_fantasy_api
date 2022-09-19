#!/bin/python

import yahoo_fantasy_api as yfa
from yahoo_fantasy_api import yhandler, League
import objectpath
import datetime
import re

# TODO: Handle as individual player instead of list of players
# TODO: How to handle single search for list of players? Separate class as list of players? (handler in League class for list of players?)

class Player(League):
    """An abstraction for the player APIs in Yahoo! fantasy

    :param sc: Fully constructed session context
    :type sc: :class:`yahoo_oauth.OAuth2`
    :param league_id: League ID for player stat context.  All API requests
        will be for this league.
    :type league_id: str
    :param player: Player ID 
    """
    def __init__(self, player):
        if isinstance(player, int):
            self.player = [player]
        self.player_details_cache = {}

    def inject_yhandler(self, yhandler):
        self.yhandler = yhandler

    def player_details(self, player):
        """
        Retrieve details about a number of players

        :parm player: If a str, this is a search string that will return all
            matches of the name (to a maximum of 25 players).  It it is a int
            or list(int), then these are player IDs to lookup.
        :return: Details of all of the players found.  If given a player ID
            that does not exist, then a RuntimeError exception is thrown.  If
            searching for players by name and none are found an empty list is
            returned.
        :rtype: list(dict)

        >>> lg.player_details('Phil Kessel')
        [{'player_key': '396.p.3983',
          'player_id': '3983',
          'name': {'full': 'Phil Kessel',
                   'first': 'Phil',
                   'last': 'Kessel',
                   'ascii_first': 'Phil',
                   'ascii_last': 'Kessel'},
          'editorial_player_key': 'nhl.p.3983',
          'editorial_team_key': 'nhl.t.24',
          'editorial_team_full_name': 'Arizona Coyotes',
          'editorial_team_abbr': 'Ari',
          'uniform_number': '81',
          'display_position': 'RW',
          'headshot': {...},
          'image_url': '...',
          'is_undroppable': '0',
          'position_type': 'P',
          'primary_position': 'RW',
          'eligible_positions': [{'position': 'RW'}],
          ...
        }]
        >>> plyrs = lg.player_details([3983, 5085, 5387])
        >>> len(plyrs)
        3
        >>> [p['name']['full'] for p in plyrs]
        ['Phil Kessel', 'Philipp Grubauer', 'Phillip Danault']
        >>> plyrs = lg.player_details('Phil')
        >>> len(plyrs)
        14
        """
        if isinstance(player, int):
            player = [player]
        self._cache_player_details(player)
        players = []
        if isinstance(player, list):
            for p in player:
                players.append(self.player_details_cache[p])
        elif player in self.player_details_cache:
            assert(isinstance(self.player_details_cache[player], list))
            players = self.player_details_cache[player]
        return players
    
    def player_stats(self, player_ids, req_type, date=None, season=None):
        """Return stats for a list of players

        :param player_ids: Yahoo! player IDs of the players to get stats for
        :type player_ids: list(int)
        :param req_type: Defines the date range for the stats.  Valid values
            are: 'season', 'average_season', 'lastweek', 'lastmonth', 'date'.
            'season' returns stats for a given season, specified by the season
            paramter.  'date' returns stats for a single date, specified by
            the date parameter.
            The 'last*' types return stats for a given time frame relative to
            the current.
        :type req_type: str
        :param date: When requesting stats for a single date, this identifies
            what date to request the stats for.  If left as None, and range
            is for a date this returns stats for the current date.
        :type date: datetime.date
        :param season: When requesting stats for a season, this identifies the
            season.  If None and requesting stats for a season, this will
            return stats for the current season.
        :type season: int
        :return: Return the stats requested.  Each entry in the list are stats
            for a single player.  The list will one entry for each player ID
            requested.
        :rtype: list(dict)

        >>> lg.player_stats([6743], 'season')
         [{'player_id': 6743,
           'name': 'Connor McDavid',
           'position_type': 'P',
           'GP': 32.0,
           'G': 19.0,
           'A': 33.0,
           'PTS': 52.0,
           '+/-': 1.0,
           'PIM': 18.0,
           'PPG': 8.0,
           'PPA': 15.0,
           'PPP': 23.0,
           'GWG': 2.0,
           'SOG': 106.0,
           'S%': 0.179,
           'PPT': 7429.0,
           'Avg-PPT': 232.0,
           'SHT': 277.0,
           'Avg-SHT': 9.0,
           'COR': -64.0,
           'FEN': -51.0,
           'Off-ZS': 310.0,
           'Def-ZS': 167.0,
           'ZS-Pct': 64.99,
           'GStr': 7.0,
           'Shifts': 684.0}]
        """
        if type(player_ids) is not list:
            player_ids = [player_ids]

        lg_settings = self.settings()
        game_code = lg_settings['game_code']
        self._cache_stats_id_map(game_code)
        stats = []
        while len(player_ids) > 0:
            next_player_ids = player_ids[0:25]
            player_ids = player_ids[25:]
            stats += self._fetch_plyr_stats(game_code, next_player_ids,
                                            req_type, date, season)
        return stats

    def _fetch_plyr_stats(self, game_code, player_ids, req_type, date, season):
        '''
        Fetch player stats for at most 25 player IDs.

        :param game_code: Game code of the players we are fetching
        :param player_ids: List of up to 25 player IDs
        :param req_type: Request type
        :param date: Date if request type is 'date'
        :param season: Season if request type is 'season'
        :return: The stats requested
        :rtype: list(dict)
        '''
        assert(len(player_ids) > 0 and len(player_ids) <= 25)
        json = self.yhandler.get_player_stats_raw(game_code, player_ids,
                                                  req_type, date, season)
        t = objectpath.Tree(json)
        stats = []
        row = None
        for e in t.execute('$..(full,player_id,position_type,stat)'):
            if 'player_id' in e:
                if row is not None:
                    stats.append(row)
                row = {}
                row['player_id'] = int(e['player_id'])
            elif 'full' in e:
                row['name'] = e['full']
            elif 'position_type' in e:
                row['position_type'] = e['position_type']
            elif 'stat' in e:
                stat_id = int(e['stat']['stat_id'])
                try:
                    val = float(e['stat']['value'])
                except ValueError:
                    val = e['stat']['value']
                if stat_id in self.stats_id_map:
                    row[self.stats_id_map[stat_id]] = val
        if row is not None:
            stats.append(row)
        return stats

    def _parse_player_detail(self, plyr):
        '''
        Helper to produce a meaningful dict for player details API
        '''
        player_data = {}
        for category in plyr:
            for sub_category in category:
                if isinstance(sub_category, str):
                    player_data[sub_category] = category[sub_category]
                elif isinstance(sub_category, dict):
                    for key, value in sub_category.items():
                        player_data[key] = value
        return player_data

    def _cache_player_details(self, player):
        '''
        Helper to ensure request for player is in the cache.
        '''
        lookup = self._calc_lookup_for_player_detail(player)
        while lookup is not None and (not isinstance(lookup, list) or
                                      len(lookup) > 0):
            if isinstance(player, list):
                ids = lookup.pop()
                t = objectpath.Tree(self.yhandler.get_player_raw(
                    self.league_id, ids=ids))
            else:
                t = objectpath.Tree(self.yhandler.get_player_raw(
                    self.league_id, search=lookup))
                key = lookup
                lookup = None

            for json in t.execute('$..players'):
                if json == []:
                    continue
                for i in range(int(json['count'])):
                    details = self._parse_player_detail(json[str(i)]['player'])
                    if isinstance(lookup, list):   # Cache by player ID
                        key = int(details['player_id'])
                        self.player_details_cache[key] = details
                    else:  # Cache by search string
                        if key not in self.player_details_cache:
                            self.player_details_cache[key] = []
                        self.player_details_cache[key].append(details)

    def _calc_lookup_for_player_detail(self, player):
        '''
        Helper to figure the players that cannot be fulfilled from cache

        :param player:  The search or id request for player_detail.  This can
            be a string to match on the name or a list of player IDs.
        :return: If player is a str, then this will return None if the str is
            already in the cache.  If player is a list, this is a list of
            lists.  The lists are player IDs we need to get from Yahoo.  This
            list can be empty if all player IDs are in the cache.
        '''
        if isinstance(player, list):
            # Figure out the players in the list that have already been fetched
            fetch_list = []
            for p in player:
                if p not in self.player_details_cache:
                    fetch_list.append(p)
            # Yahoo only returns 25 players at a time
            split_list = []
            while len(fetch_list) > 0:
                if len(fetch_list) > 25:
                    split_list.append(fetch_list[-25:])
                    del fetch_list[-25:]
                else:
                    split_list.append(fetch_list)
                    fetch_list = []
            return split_list
        elif player in self.player_details_cache:
            return None
        else:
            return player

    def _cache_stats_id_map(self, game_code):
        '''Ensure the self.stats_id_map is setup

        The self.stats_id_map will map the stat ID to a display name.
        '''
        if self.stats_id_map is None:
            json = self.yhandler.get_settings_raw(self.league_id)
            t = objectpath.Tree(json)
            # Start with the static map of category ID map.  The stats API
            # generates a lot of stats, where as the ones we are getting the
            # settings are only the categories that scoring is based on.
            stats_id_map = self._get_static_id_map(game_code)
            for s in t.execute('$..stat_categories..(stat_id,display_name)'):
                stats_id_map[int(s['stat_id'])] = s['display_name']
            self.stats_id_map = stats_id_map

    def _get_static_id_map(self, game_code):
        '''
        Get a static map of ID to stat names for specific sport

        If we lookup in league settings for a list of category names, it will
        just include the scoring categories for the fantasy league.  These
        static maps allow us to access additional stats.
        '''
        if game_code == 'mlb':
            return self._get_static_mlb_id_map()
        elif game_code == 'nhl':
            return self._get_static_nhl_id_map()
        else:
            return {}

    def _get_static_mlb_id_map(self):
        '''
        Return a map that returns a statement given ID.

        This is tailored for major league baseball.
        '''
        return {0: 'G', 2: 'GS', 3: 'AVG', 4: 'OBP', 5: 'SLG', 6: 'AB', 7: 'R',
                8: 'H', 9: '1B', 10: '2B', 11: '3B', 12: 'HR', 13: 'RBI',
                14: 'SH', 15: 'SF', 16: 'SB', 17: 'CS', 18: 'BB', 19: 'IBB',
                20: 'HBP', 21: 'SO', 22: 'GDP', 23: 'TB', 25: 'GS', 26: 'ERA',
                27: 'WHIP', 28: 'W', 29: 'L', 32: 'SV', 34: 'H', 35: 'BF',
                36: 'R', 37: 'ER', 38: 'HR', 39: 'BB', 40: 'IBB', 41: 'HBP',
                42: 'K', 43: 'BK', 44: 'WP', 48: 'HLD', 50: 'IP', 51: 'PO',
                52: 'A', 53: 'E', 54: 'FLD%', 55: 'OPS', 56: 'SO/W', 57: 'SO9',
                65: 'PA', 84: 'BS', 85: 'NSV', 87: 'DP',
                1032: 'FIP', 1021: 'GB%', 1022: 'FB%', 1031: 'BABIP',
                1036: 'HR/FB%', 1037: 'GB', 1038: 'FB', 1020: 'GB/FB',
                1018: 'P/IP', 1034: 'ERA-', 1019: 'P/S', 1024: 'STR',
                1025: 'IRS%', 1026: 'RS', 1027: 'RS/9', 1028: 'AVG',
                1029: 'OBP', 1030: 'SLG', 1033: 'WAR',
                1035: 'HR/FB%', 1008: 'GB/FB', 1013: 'BABIP', 1002: 'ISO',
                1001: 'CT%', 1014: 'wOBA', 1015: 'wRAA', 1011: 'RC',
                1005: 'TOB', 1006: 'GB', 1009: 'GB%', 1007: 'FB', 1010: 'FB%',
                1016: 'OPS+', 1004: 'P/PA', 1039: 'SB%', 1012: 'GDPR',
                1003: 'SL', 1017: 'FR', 1040: 'bWAR', 1041: 'brWAR',
                1042: 'WAR'}

    def _get_static_nhl_id_map(self):
        '''
        Return a map that returns a statement given ID.

        This is tailored for NHL.
        '''
        return {0: 'GP', 1: 'G', 2: 'A', 3: 'PTS', 4: '+/-', 5: 'PIM',
                6: 'PPG', 7: 'PPA', 8: 'PPP', 12: 'GWG', 14: 'SOG', 15: 'S%',
                18: 'GS', 19: 'W', 20: 'L', 22: 'GA', 23: 'GAA',
                24: 'SA', 25: 'SV', 26: 'SV%', 27: 'SHO', 28: 'MIN',
                1001: 'PPT', 1002: 'Avg-PPT', 1003: 'SHT', 1004: 'Avg-SHT',
                1005: 'COR', 1006: 'FEN', 1007: 'Off-ZS', 1008: 'Def-ZS',
                1009: 'ZS-Pct', 1010: 'GStr', 1011: 'Shifts'}