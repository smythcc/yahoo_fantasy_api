#!/bin/python

import yahoo_fantasy_api as yfa
from yahoo_fantasy_api import yhandler
import objectpath
import datetime
import re


class League:
    """An abstraction for all of the league-level APIs in Yahoo! fantasy

    :param sc: Fully constructed session context
    :type sc: :class:`yahoo_oauth.OAuth2`
    :param league_id: League ID to setup this class for.  All API requests
        will be for this league.
    :type league_id: str
    """
    def __init__(self, sc, league_id):
        self.sc = sc
        self.league_id = league_id
        self.yhandler = yhandler.YHandler(sc)
        self.current_week_cache = None
        self.end_week_cache = None
        self.week_date_range_cache = {}
        self.free_agent_cache = {}
        self.waivers_cache = None
        self.taken_players_cache = None
        self.stat_categories_cache = None
        self.settings_cache = None
        self.edit_date_cache = None
        self.positions_cache = None
        self.stats_id_map = None

    def inject_yhandler(self, yhandler):
        self.yhandler = yhandler

    def to_team(self, team_key):
        """Construct a Team object from a League

        :param team_key: Team key of the new Team object to construct
        :type team_key: str
        :return: Fully constructed object
        :rtype: Team
        """
        tm = yfa.Team(self.sc, team_key)
        tm.inject_yhandler(self.yhandler)
        return tm

    def standings(self):
        """Return the standings of the league id

        For each team in the standings it returns info about their place in the
        standings (e.g. w/l record, number of games back).

        :return: An ordered list of the teams in the standings.  First entry is
            the first place team.
        :rtype: List

        >>> lg.standings()[0]
        {'team_key': '388.l.27081.t.5',
         'name': 'Lumber Kings',
         'rank': 1,
         'playoff_seed': '5',
         'outcome_totals': {'wins': '121',
          'losses': '116',
          'ties': '15',
          'percentage': '.510'},
         'games_back': '19'}
        """
        json = self.yhandler.get_standings_raw(self.league_id)
        t = objectpath.Tree(json)
        num_teams = int(t.execute('$..count[0]'))
        standings = []
        for i in range(num_teams):
            team = {}
            for e in t.execute('$..teams.."{}".team[0]'.format(i)):
                if isinstance(e, list):
                    for td in e:
                        if "team_key" in td or 'name' in td:
                            self._merge_dicts(team, td, [])
                elif "team_standings" in e:
                    self._merge_dicts(team, e['team_standings'], [])
            standings.append(team)
        return standings

    def teams(self):
        """Return details of all of the teams in the league.

        :return: A dictionary of teams, each entry is for a team.  The team key
            is the key to the dict, where the values are all of the particulars
            for that team.
        :rtype: dict

        >>> tms = lg.teams()
        >>> tms.keys()
        dict_keys(['388.l.27081.t.5', '388.l.27081.t.1', '388.l.27081.t.3',
                   '388.l.27081.t.7', '388.l.27081.t.8', '388.l.27081.t.4',
                   '388.l.27081.t.2', '388.l.27081.t.9', '388.l.27081.t.6',
                   '388.l.27081.t.10'])
        >>> tms['388.l.27081.t.5'].keys()
        dict_keys(['team_key', 'team_id', 'name', 'is_owned_by_current_login',
                   'url', 'team_logos', 'waiver_priority', 'number_of_moves',
                   'number_of_trades', 'roster_adds', 'clinched_playoffs',
                   'league_scoring_type', 'has_draft_grade',
                   'auction_budget_total', 'auction_budget_spent', 'managers'])
        """
        json = self.yhandler.get_standings_raw(self.league_id)
        t = objectpath.Tree(json)
        num_teams = int(t.execute('$..count[0]'))
        teams = {}
        for i in range(num_teams):
            team = {}
            key = None
            for e in t.execute('$..teams.."{}".team[0][0]'.format(i)):
                if "team_key" in e:
                    key = e['team_key']
                if isinstance(e, dict):
                    self._merge_dicts(team, e, [])
            teams[key] = team
        return teams

    def matchups(self, week=None):
        """Retrieve matchups data for a given week. Defaults to current week.

        :param week: Week to request, defaults to None
        :type week: int, optional
        :return: Matchup details as key/value pairs
        :rtype: dict
        """
        json = self.yhandler.get_scoreboard_raw(self.league_id, week=week)
        return json

    def settings(self):
        """Return the league settings

        :return: League settings as key/value pairs
        :rtype: Dict

        >>> lg.setings()
        {'league_key': '398.l.10372', 'league_id': '10372', 'name': "Buck you're next!",
         'url': 'https://baseball.fantasysports.yahoo.com/b1/10372', 'logo_url': False,
         'draft_status': 'predraft', 'num_teams': 9, 'edit_key': '2020-02-03',
         'weekly_deadline': '1', 'league_update_timestamp': None, 'scoring_type': 'head',
         'league_type': 'private', 'renew': '388_27081', 'renewed': '',
         'iris_group_chat_id': 'ZP2QUJTUB5CPXMXWAVSYZRJI3Y', 'allow_add_to_dl_extra_pos': 0,
         'is_pro_league': '0', 'is_cash_league': '0', 'current_week': '1', 'start_week': '1',
         'start_date': '2020-03-26', 'end_week': '24', 'end_date': '2020-09-20',
         'game_code': 'mlb', 'season': '2020', 'draft_type': 'self', 'is_auction_draft': '0',
         'uses_playoff': '1', 'has_playoff_consolation_games': True, 'playoff_start_week': '22',
         'uses_playoff_reseeding': 1, 'uses_lock_eliminated_teams': 0, 'num_playoff_teams': '6',
         'num_playoff_consolation_teams': 6, 'has_multiweek_championship': 0,
         'uses_roster_import': '1', 'roster_import_deadline': '2020-03-25', 'waiver_type': 'R',
         'waiver_rule': 'all', 'uses_faab': '0', 'draft_pick_time': '60',
         'post_draft_players': 'FA', 'max_teams': '14', 'waiver_time': '2',
         'trade_end_date': '2020-08-09', 'trade_ratify_type': 'vote', 'trade_reject_time': '2',
         'player_pool': 'ALL', 'cant_cut_list': 'none', 'can_trade_draft_picks': '1'}
        """  # noqa
        if self.settings_cache is None:
            json = self.yhandler.get_settings_raw(self.league_id)
            data = {}
            if "fantasy_content" in json:
                content = json["fantasy_content"]
                if "league" in content:
                    self._merge_dicts(data, content["league"][0], [])
                    # Filtering out 'roster_positions' and 'stat_categories'
                    # because they can be found in other APIs.
                    self._merge_dicts(data,
                                      content["league"][1]["settings"][0],
                                      ["roster_positions", "stat_categories"])
            self.settings_cache = data
        return self.settings_cache

    def stat_categories(self):
        """Return the stat categories for a league

        :returns: Each dict entry will have the stat name along
            with the position type ('B' for batter or 'P' for pitcher).
        :rtype: list(dict)

        >>> lg.stat_categories('370.l.56877')
        [{'display_name': 'R', 'position_type': 'B'}, {'display_name': 'HR',
        'position_type': 'B'}, {'display_name': 'W', 'position_type': 'P'}]
        """
        if self.stat_categories_cache is None:
            t = objectpath.Tree(self.yhandler.get_settings_raw(self.league_id))
            json = t.execute('$..stat_categories..stat')
            simple_stat = []
            for s in json:
                # Omit stats that are only for display purposes
                if 'is_only_display_stat' not in s:
                    simple_stat.append({"display_name": s["display_name"],
                                        "position_type": s["position_type"]})
            self.stat_categories_cache = simple_stat
        return self.stat_categories_cache

    def team_key(self):
        """Return the team_key for logged in users team in this league

        :return: The team key
        :rtype: str

        >>> lg.team_key()
        388.l.27081.t.5
        """
        t = objectpath.Tree(self.yhandler.get_teams_raw())
        json = t.execute('$..(team_key)')
        for t in json:
            if t['team_key'].startswith(self.league_id):
                return t['team_key']

    def current_week(self):
        """Return the current week number of the league

        :return: Week number
        :rtype: int

        >>> lg.current_week()
        12
        """
        if self.current_week_cache is None:
            t = objectpath.Tree(self.yhandler.get_scoreboard_raw(
                self.league_id))
            self.current_week_cache = int(t.execute('$..current_week[0]'))
        return self.current_week_cache

    def end_week(self):
        """Return the ending week number of the league.

        :return: Week number
        :rtype: int

        >>> lg.end_week()
        24
        """
        if self.end_week_cache is None:
            t = objectpath.Tree(
                self.yhandler.get_scoreboard_raw(self.league_id))
            self.end_week_cache = int(t.execute('$..end_week[0]'))
        return self.end_week_cache

    def week_date_range(self, week):
        """Return the start and end date of a given week.

        Can only request the date range at most one week in the future.  This
        restriction exists because Yahoo! only provides the week range when the
        matchups are known.  And during the playoffs, the matchup is only known
        for the current week.  A :class:`RuntimeError` exception is returned if
        a request is for a week too far in the future.

        :return: Start and end date of the given week
        :rtype: Tuple of two :class:`datetime.date` objects

        >>> lg.week_date_range(12)
        (datetime.date(2019, 6, 17), datetime.date(2019, 6, 23))
        """
        if week <= self.current_week() or week == 1:
            return self._date_range_of_played_or_current_week(week)
        elif week == self.current_week() + 1:
            (cur_st, cur_end) = self._date_range_of_played_or_current_week(
                week - 1)
            req_st = cur_end + datetime.timedelta(days=1)
            req_end = cur_end + datetime.timedelta(days=7)
            return (req_st, req_end)
        else:
            raise RuntimeError("Cannot request date range more than one week "
                               "past the current week.  The requested week is "
                               "{}, but current week is {}.".format(
                                   week, self.current_week()))

    def free_agents(self, position):
        """Return the free agents for the given position

        :param position: All free agents must be able to play this position.
             Use the short code of the position (e.g. 2B, C, etc.).  You can
             also specify the position type (e.g. 'B' for all batters and 'P'
             for all pitchers).
        :type position: str
        :return: Free agents found. Particulars about each free agent will be
             returned.
        :rtype: List(Dict)

        >>> fa_CF = lg.free_agents('CF')
        >>> len(fa_CF)
        60
        >>> fa_CF[0]
        {'player_id': 8370,
         'name': 'Dexter Fowler',
         'position_type': 'B',
         'eligible_positions': ['CF', 'RF', 'Util']}
        """
        if position not in self.free_agent_cache:
            self.free_agent_cache[position] = self._fetch_players(
                'FA', position=position)
        return self.free_agent_cache[position]

    def waivers(self):
        """Return the players currently on waivers.

        :return: Players on waiver.
        :rtype: List(dict)

        >>> lg.waivers()
        [{'player_id': 5986,
          'name': 'Darnell Nurse',
          'position_type': 'P',
          'eligible_positions': ['D'],
          'percent_owned': 65,
          'status': ''},
         {'player_id': 5999,
          'name': 'Anthony Mantha',
          'status': 'IR',
          'position_type': 'P',
          'eligible_positions': ['LW', 'RW', 'IR'],
          'percent_owned': 84},
         {'player_id': 7899,
          'name': 'Rasmus Dahlin',
          'status': 'IR',
          'position_type': 'P',
          'eligible_positions': ['D', 'IR'],
          'percent_owned': 87}]
        """
        if not self.waivers_cache:
            self.waivers_cache = self._fetch_players('W')
        return self.waivers_cache

    def taken_players(self):
        """Return the players taken by teams.

        :return: Players taken by teams.
        :rtype: List(dict)

        >>> tp = lg.taken_players()
        >>> len(tp)
        88
        >>> tp[0]
        {'player_id': 3341,
         'name': 'Marc-Andre Fleury',
         'position_type': 'G',
         'eligible_positions': ['G'],
         'percent_owned': 99,
         'status': ''}
        """
        if not self.taken_players_cache:
            self.taken_players_cache = self._fetch_players('T')
        return self.taken_players_cache

    def _fetch_players(self, status, position=None):
        """Fetch players from Yahoo!

        :param status: Indicates what type of players to get.  Available
            options are: 'FA' for free agents, 'W' waivers only, 'T' all taken
            players, 'K' keepers, 'A' all available players (FA + WA).
        :type status: str
        :param position: An optional parameter that allows you to filter on a
            position to type of player.  If None, this option is ignored.
        :type postition: str
        :return: Players found.
        :rtype: List(Dict)
        """
        # The Yahoo! API we use doles out players 25 per page.  We need to make
        # successive calls to gather all of the players.  We stop when we fetch
        # less then 25.
        PLAYERS_PER_PAGE = 25
        plyrs = []
        plyrIndex = 0
        while plyrIndex % PLAYERS_PER_PAGE == 0:
            j = self.yhandler.get_players_raw(self.league_id, plyrIndex,
                                              status, position=position)
            (num_plyrs_on_pg, fa_on_pg) = self._players_from_page(j)
            if len(fa_on_pg) == 0:
                break
            plyrs += fa_on_pg
            plyrIndex += num_plyrs_on_pg
        return plyrs

    def _players_from_page(self, page):
        """Extract the players from a given JSON page

        This is to used with _fetch_players.

        :param page: JSON page to extract players from
        :type page: dict
        :return: A tuple returning the number of players on the page, and the
        list of players extracted from the page.
        :rtype: (int, list(dict))
        """
        fa = []

        if len(page['fantasy_content']['league'][1]['players']) == 0:
            return (0, fa)

        t = objectpath.Tree(page)
        pct_owns = self._pct_owned_from_page(iter(list(t.execute(
            '$..percent_owned.(coverage_type,value)'))))
        # When iterating over the players we step by 2 to account for the
        # percent_owned data that is stored adjacent to each player.
        for i, pct_own in zip(range(0, t.execute('$..players.count[0]')*2, 2),
                              pct_owns):
            path = '$..players..player[{}].'.format(i) + \
                "(name,player_id,position_type,status,eligible_positions)"
            obj = list(t.execute(path))
            plyr = {}
            # Convert obj from a list of dicts to a single one-dimensional dict
            for ele in obj:
                for k in ele.keys():
                    plyr[k] = ele[k]
            plyr['player_id'] = int(plyr['player_id'])
            plyr['name'] = plyr['name']['full']
            # We want to return eligible positions in a concise format.
            plyr['eligible_positions'] = [e['position'] for e in
                                          plyr['eligible_positions']]
            plyr['percent_owned'] = pct_own
            if "status" not in plyr:
                plyr["status"] = ""

            # Ignore players that are not active
            if plyr["status"] != "NA":
                fa.append(plyr)
        return (i/2 + 1, fa)

    def _pct_owned_from_page(self, po_it):
        """Extract the ownership % of players taken from a player JSON dump

        Why does this function even need to exist?  When requesting ownership
        percentage when getting players, the ownership percentage is
        included adjacent to the rest of the player data.  So it cannot be
        retrieved easily along side the player data and must be extracted
        separately.

        :param po_it: Extracted ownership % from objectpath
        :type eles: iterator over a list
        :return: Ownership percentages of each player on the JSON page
        :rtype: list(int)
        """
        po = []
        i = 0
        try:
            while True:
                ele = next(po_it)
                if "coverage_type" in ele:
                    po.append(0)
                    i += 1
                if "value" in ele:
                    po[i-1] = ele['value']
        except StopIteration:
            pass
        return po

    def _date_range_of_played_or_current_week(self, week):
        """Get the date range of a week that was already played or the current

        Assumes caller has already verified the week is no greater then
        current.

        :param week: Week to request
        :return: Start and end date of the given week
        :rtype: Tuple of two :class: datetime.date objects
        """
        if week not in self.week_date_range_cache:
            t = objectpath.Tree(self.yhandler.get_scoreboard_raw(
                self.league_id, week))
            j = t.execute('$..(week_start,week_end)[0]')
            self.week_date_range_cache[week] = (
                datetime.datetime.strptime(j['week_start'], "%Y-%m-%d").date(),
                datetime.datetime.strptime(j['week_end'], "%Y-%m-%d").date())
        return self.week_date_range_cache[week]

    def percent_owned(self, player_ids):
        """Retrieve ownership percentage of a list of players

        :param player_ids: Yahoo! Player IDs to retrieve % owned for
        :type player_ids: list(int)
        :return: Ownership percentage of players requested
        :rtype: dict

        >>> lg.percent_owned(1, [3737, 6381, 4003, 3705])
        [{'player_id': 3737, 'name': 'Sidney Crosby', 'percent_owned': 100},
         {'player_id': 6381, 'name': 'Dylan Larkin', 'percent_owned': 89},
         {'player_id': 4003, 'name': 'Semyon Varlamov', 'percent_owned': 79},
         {'player_id': 3705, 'name': 'Dustin Byfuglien', 'percent_owned': 82}]
        """
        t = objectpath.Tree(self.yhandler.get_percent_owned_raw(
            self.league_id, player_ids))
        player_ids = t.execute("$..player_id")
        it = t.execute("$..(player_id,full,value)")
        po = []
        try:
            while True:
                plyr = {"player_id": int(next(it)["player_id"]),
                        "name": next(it)["full"],
                        "percent_owned": next(it)["value"]}
                po.append(plyr)
        except StopIteration:
            pass
        return po


    def ownership(self, player_ids):
        """Retrieve the owner of a player

        :param player_ids: Yahoo! Player IDs to retrieve owned for
        :type player_ids: list(int)
        :return: Ownership status of player
        :rtype: dict

        >>> lg.ownership([3737])
        {"3737" : {"ownership_tpye" : "team", "owner_team_name": "team name"}}
        """
        t = objectpath.Tree(self.yhandler.get_player_ownership_raw(self.league_id, player_ids))
        owner_details = t.execute("$..(player_id,ownership_type,owner_team_name)")
        ownership = {}
        try:
            while True:
                player_id = next(owner_details)['player_id']
                ownership_details = next(owner_details)
                ownership[player_id] = ownership_details
        except StopIteration:
            pass
        return ownership

    def edit_date(self):
        """Return the next day that you can edit the lineups.

        :return: edit date
        :rtype: :class: datetime.date
        """
        if self.edit_date_cache is None:
            json = self.yhandler.get_settings_raw(self.league_id)
            t = objectpath.Tree(json)
            edit_key = t.execute('$..edit_key[0]')
            self.edit_date_cache = \
                datetime.datetime.strptime(edit_key, '%Y-%m-%d').date()
        return self.edit_date_cache

    def positions(self):
        """Return the positions that are used in the league.

        :return: Dictionary of positions.  Each key is a position, with a count
            and position type as the values.
        :rtype: dict(dict(position_type, count))

        >>> lg.positions()
        {'C': {'position_type': 'P', 'count': 2},
         'LW': {'position_type': 'P', 'count': 2},
         'RW': {'position_type': 'P', 'count': 2},
         'D': {'position_type': 'P', 'count': 4},
         'G': {'position_type': 'G', 'count': 2},
         'BN': {'count': 2},
         'IR': {'count': '3'}}
        """
        if self.positions_cache is None:
            json = self.yhandler.get_settings_raw(self.league_id)
            t = objectpath.Tree(json)
            pmap = {}
            for p in t.execute('$..roster_position'):
                pmap[p['position']] = {}
                for k, v in p.items():
                    if k == 'position':
                        continue
                    if k == 'count':
                        v = int(v)
                    pmap[p['position']][k] = v
            self.positions_cache = pmap
        return self.positions_cache

    def draft_results(self):
        '''
        Get the results of the league's draft

        This will return details about each pick made in the draft.  For
        auction style drafts it includes the auction price paid for the
        player.

        The players are returned as player IDs.  Use the player_details() API
        to find more specifics on the player.

        If this is called for a league that has not yet done a draft then it
        will return an empty list.

        If this is called during the draft this includes the players that have
        been drafted thus far.  For auction style drafts, it does not include
        the player currently being nominated.

        :return: Details about all of the players drafted.
        :rtype: list

        >>> draft_res = lg.draft_results()
        >>> len(draft_res)
        210
        >>> draft_res[0]
        {'pick': 1,
         'round': 1,
         'cost': '4',
         'team_key': '388.l.27081.t.4',
         'player_id': 9490}
        '''
        j = self.yhandler.get_draftresults_raw(self.league_id)
        t = objectpath.Tree(j)
        dres = []
        pat = re.compile(r'.*\.p\.([0-9]+)$')
        for p in t.execute('$..draft_results..draft_result'):
            pk = p['player_key']
            m = pat.search(pk)
            if m:
                pid = int(m.group(1))
                p['player_id'] = pid
                del p['player_key']
            dres.append(p)
        return(dres)

    def transactions(self, tran_types, count):
        '''
        Fetch transactions of a given type for the league.

        :param tran_types: The comman seperated types of transactions retrieve.  Valid values
            are: add,drop,commish,trade
        :type tran_types: str
        :param count: The number of transactions to retrieve. Leave blank to return all
            transactions
        :type count: str

        :return: Details about all the transactions from the league of a given type
        :rtype: list

        >>> transactions('trade', '1')
        [
            {'players': {...}, 'status': 'successful', 'timestamp': '1605168906', 'tradee_team_key': '399.l.710921.t.3', 'tradee_team_name': 'Red Skins Matter', 'trader_team_key': '399.l.710921.t.9', 'trader_team_name': 'Too Many Cooks', 'transaction_id': '319', 'transaction_key': '399.l.710921.tr.319', ...}, 
            {'players': {...}, 'status': 'successful', 'timestamp': '1604650727', 'tradee_team_key': '399.l.710921.t.5', 'tradee_team_name': 'Nuklear JuJu Charks', 'trader_team_key': '399.l.710921.t.2', 'trader_team_name': 'JuJus Golden Johnson', 'transaction_id': '295', 'transaction_key': '399.l.710921.tr.295', ...}, 
            {'players': {...}, 'status': 'successful', 'timestamp': '1601773444', 'tradee_team_key': '399.l.710921.t.4', 'tradee_team_name': 'DJ chark juju juju', 'trader_team_key': '399.l.710921.t.9', 'trader_team_name': 'Too Many Cooks', 'transaction_id': '133', 'transaction_key': '399.l.710921.tr.133', ...}
        ]
        '''
        j = self.yhandler.get_transactions_raw(self.league_id, tran_types, count)
        t = objectpath.Tree(j).execute('$..transactions..transaction')
        transactions = []
        for transaction_details in t:
            players = next(t)
            transactions.append({**transaction_details, **players})
        return transactions

    def _merge_dicts(self, target, source, filter):
        '''
        Helper to merge two dicts together
        '''
        assert(isinstance(source, dict))
        assert(isinstance(target, dict))
        for key, value in source.items():
            if key not in filter:
                target[key] = value