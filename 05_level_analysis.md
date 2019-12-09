# Исследование зависимости конверсии и платежей от выбранного уровня сложности

Задания:

проверить два предположения:

- Зависит ли вероятность оплаты от выбранного пользователем уровня сложности бесплатных тренировок?
- Существует ли разница во времени между выбором уровня сложности и оплатой между пользователями, выбирающими разные уровни сложности?

Ограничения: 

- результат должен быть в Jupyter Notebook.
- Данные пользователей, зарегистрированных в 2017 г.

Поскольку работаем в Jupyter, и база не моя, нельзя использовать представления и временные таблицы. Будем выкручиваться через CTE.

Импорт библиотек, определение констант:

```
import pandas as pd
import psycopg2
import matplotlib.pyplot as plt

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

# Только покупатели
BUYERS_TMPL = """
    SELECT DISTINCT user_id
    FROM case8.purchase
    INTERSECT
    SELECT DISTINCT user_id
    FROM case8.events
    WHERE event_type = 'registration'
    AND start_time BETWEEN '{0}' AND '{1}'
"""

# Теперь выделим пользователей и покупателей заданного временного диапазона
ALL_USERS = ALL_USERS_TMPL.format(START_DATE, END_DATE)
BUYERS    = BUYERS_TMPL.format(START_DATE, END_DATE)

# и запишем CTE для этих групп (Практически списков USER_ID - ов)
USERS17_CTE = """users_2017 as (
        {}
    )
""".format(ALL_USERS)

BUYERS17_CTE = """buyers_2017 as (
        {}
   )
""".format(BUYERS)

```
