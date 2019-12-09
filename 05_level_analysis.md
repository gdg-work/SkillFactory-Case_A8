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
USERS   = ALL_USERS_TMPL.format(START_DATE, END_DATE)
BUYERS  = BUYERS_TMPL.format(START_DATE, END_DATE)

# и запишем CTE для этих групп (Практически списков USER_ID - ов)
USERS17_CTE = """users_2017 as (
    {}
)""".format(USERS)

BUYERS17_CTE = """buyers_2017 as (
    {} 
)""".format(BUYERS)

# Вместо представлений определим CTE для событий, производимых пользователями 2017 года регистрации, и их покупок
EVENTS17_CTE = """events_2017 as (
    select * from case8.events
    inner join
    users_2017
    using (user_id)
)"""

PURCHASES17_CTE = """purchases_2017 as (
    select * from case8.purchase
    inner join
    users_2017
    using (user_id)
)"""
```

Вооружившись таким набором констант, соберём на стороне сервера CTE для списков пользователей, выбирающих разные уровни сложности
в приложении.  Уровней у нас всего три: `hard`, `medium` и  `easy`.  Будут и три CTE: для трудного, среднего и лёгкого уровней,
общий формат имён CTE: `<level>_users_17`:


```
LVL_CTE_TMPL = """{0}_users_2017 as (
    SELECT DISTINCT user_id
    FROM events_2017 
    WHERE event_type = 'level_choice' AND
    selected_level = '{0}'
)"""

HARD_USERS_CTE = LVL_CTE_TMPL.format('hard')
MEDIUM_USERS_CTE = LVL_CTE_TMPL.format('medium')
EASY_USERS_CTE = LVL_CTE_TMPL.format('easy')
```

И мы почти готовы посчитать конверсию по пользвователям разных уровней сложности:

```
curr_cte = 'with ' + ', '.join((USERS17_CTE, EVENTS17_CTE, PURCHASES17_CTE,  HARD_USERS_CTE, MEDIUM_USERS_CTE, EASY_USERS_CTE))

lvl_req_template = """
select
    count(user_id) as total_users,
    count(amount)  as buyers,
    sum(amount)    as revenue,
    count(amount)*1.0/count(user_id) as "conversion",
    avg(amount)    as avg_check
from 
    {}_users_2017
    left join 
    purchases_2017 
    using (user_id)
"""
conversion_request = curr_cte + " " + " UNION ALL ".join([lvl_req_template.format(lvl) for lvl in ('hard', 'medium', 'easy')]) + ";"
print("Will execute SQL query:\n" + conversion_request)

db_conn.execute(conversion_request)
ret = db_conn.fetchall()

conv_df = pd.DataFrame(ret, columns=('users', 'buyers', 'revenue', 'conversion', 'avg_check'), index=('hard', 'medium', 'easy'))
print(conv_df.to_string(formatters={'conversion': '{:.2%}'.format, 'avg_check': '{:.2f} р.'.format}))
```

В результате выводится табличка:

| level    | users   |  buyers    | conversion |  avg_check |
|:---------|--------:|-----------:|-----------:|-----------:|
| hard     | 1249    | 442        | 35.39%     | 111.60 р.  |
| medium   | 4645    | 969        | 20.86%     | 109.52 р.  |
| easy     | 2448    | 189        | 7.72%      | 114.95 р.  |


