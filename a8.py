#!/usr/bin/env python
import pandas as pd
import psycopg2


# there are two modules with only constants defined: one for local DB
# and another for remote (SkillFactory) database. Only one to be enabled
# in any given time
# ---
# from SkillFactory_DB import DB_NAME, DB_USER, DB_HOST, DB_PORT, DB_PASSWD
from Local_DB        import DB_NAME, DB_USER, DB_HOST, DB_PORT, DB_PASSWD


# constants
DB_CONNECT_STRING = "dbname={0} host={1} port={2} user={3} password={4}".format(
    DB_NAME, DB_HOST, DB_PORT, DB_USER, DB_PASSWD
)
START_DATE = '2017-01-01'   # this day will be included
END_DATE   = '2018-01-01'   # and this will be not

# template for SQL expression: all users registered btw two dates list
ALL_USERS_TMPL = """
    SELECT DISTINCT user_id
    FROM case8.events
    WHERE event_type = 'registration'
    AND start_time BETWEEN '{0}' AND '{1}'
"""

ALL_USERS = ALL_USERS_TMPL.format(START_DATE, END_DATE)

# Template for SQL query. Parameters:
# 0 - table alias,
# 1 - list of fields to get or '*'
# 2 - name of table to query
QUERY_TMPL = ("""
WITH
all_users as (
{0}
)
""".format(ALL_USERS) + "\n" +
""" SELECT {0}.{1}
 FROM {2} as {0} join all_users using(user_id);
""")

purchases_query = QUERY_TMPL.format('p', '*', 'case8.purchase')
events_query = QUERY_TMPL.format('e','*','case8.events')


def init_connect(conn_string) -> psycopg2.extensions.cursor:
    db_conn = psycopg2.connect(conn_string)
    cursor = None
    if db_conn:
        db_conn.set_session(readonly=True,autocommit=True)
        cursor = db_conn.cursor()
    return cursor

if __name__ == "__main__":
    cursor = init_connect(DB_CONNECT_STRING)
    cursor.execute(purchases_query)
    purchases = cursor.fetchall()
    cursor.execute(events_query)
    events = cursor.fetchall()

    # Это немножко читерство: мы выбираем все действия всех пользователей, зарегистрированных в 2017 г.
    events_df = pd.DataFrame(events, columns=('event_type', 'selected_level', 'start_time', 'tutorial_id', 'user_id', 'id'))
    purchases_df = pd.DataFrame(purchases, columns=('user_id', 'start_time', 'amount', 'id')) 
