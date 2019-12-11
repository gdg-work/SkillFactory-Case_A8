# Исследование зависимости конверсии и платежей от выбранного уровня сложности

## Цель работы

### Гипотезы

проверить два предположения:

- Зависит ли вероятность оплаты от выбранного пользователем уровня сложности бесплатных тренировок?
- Существует ли разница во времени между выбором уровня сложности и оплатой между пользователями, выбирающими разные уровни сложности?

### Ограничения: 

- результат должен быть в Jupyter Notebook.
- Данные пользователей, зарегистрированных в 2017 г.

Поскольку работаем в Jupyter, и база не моя, нельзя использовать представления и временные таблицы. Будем выкручиваться через CTE.

### Дополнительные условия

В учебной базе объём данных не слишком серьёзный.  Но при обработке данных из БД
обычна ситуация, когда данных больше, чем может вместиться в памяти (особенно в
памяти персонального компьютера). К счастью, все данные и не нужно тащить в память —
у нас есть целая СУБД, которая сделает любые выборки, объединения и сортировки.
Нужно только правильно ей пользоваться.


## За работу!

Импорт библиотек:

```
import pandas as pd
import psycopg2
import matplotlib.pyplot as plt
```
Определение констант:

Чтобы не хранить пароли в ГитХабе (порочная практика :) ), записал их в отдельные
файлы и подключаю через импорт.

```
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
```

Начальное и конечное время для исследования.  Первое включается в диапазон, второе нет.

```
START_DATE = '2017-01-01'   # this day will be included
END_DATE   = '2018-01-01'   # and this will be not
```

Далее множество шаблонов для CTE и SQL запросов.

```
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

# Вместо представлений определим CTE для событий, производимых пользователями
# 2017 года регистрации, и их покупок
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

## Зависит ли вероятность оплаты от выбранного пользователем уровня сложности бесплатных тренировок?

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

Определю функцию, которая соединяется с базой, настраивает параметры соединения, 
создаёт курсор и возвращает его.

```
def init_connect(conn_string: "PostgreSQL connection string") -> psycopg2.extensions.cursor:
    """Connect to DB using connection string from 1st parameter. Return the cursor"""
    db_conn = psycopg2.connect(conn_string)
    cursor = None
    if db_conn:
        db_conn.set_session(readonly=True,autocommit=True)
        cursor = db_conn.cursor()
    return cursor
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

##
## XXX Не проще ли тут использовать group by в запросе?
##

conversion_request = curr_cte + " " + " UNION ALL ".join([lvl_req_template.format(lvl) for lvl in ('hard', 'medium', 'easy')]) + ";"
print("Will execute SQL query:\n" + conversion_request)

cursor = init_connect(DB_CONNECT_STRING)
cursor.execute(conversion_request)
ret = cursor.fetchall()

conv_df = pd.DataFrame(ret, columns=('users', 'buyers', 'revenue', 'conversion', 'avg_check'), index=('hard', 'medium', 'easy'))
print(conv_df.to_string(formatters={'conversion': '{:.2%}'.format, 'avg_check': '{:.2f} р.'.format}))
```

В результате выводится табличка:

| level    | users   |  buyers    | revenue   | conversion |  avg_check |
|:---------|--------:|-----------:|----------:|-----------:|-----------:|
| hard     | 1249    | 442        |    49235  | 35.39%     | 111.60 р.  |
| medium   | 4645    | 969        |   106125  | 20.86%     | 109.52 р.  |
| easy     | 2448    | 189        |    21725  | 7.72%      | 114.95 р.  |

### Вывод по первому вопросу: 

Существует зависимость между уровнем сложности и конверсией. Пользователи, которые выбирают уровни
_hard_ и _medium_, чаще оплачивают тренировки.  При этом больше всего прибыли приносят пользователи
уровня _medium_ за счёт большего числа таких пользователей.

Зависимости между средним чеком и уровнем сложности тренировок не обнаружено.

## Исследование временных промежутков между выбором уровня и оплатой.

Нужно построить представление, в котором будет колонки: `user_id`, `selected_level`,
`level_choice_time_stamp`, `purchase_time_stamp`, `time_difference`.  Названия говорят
сами за себя.  Для этого объединим CTE `events_2017` и `purchases_2017` через INNER JOIN
по полю `user_id`, тогда останутся только покупатели.

```
curr_cte = 'with ' + ', '.join((USERS17_CTE, EVENTS17_CTE, PURCHASES17_CTE))

cursor.execute(curr_cte + """
select 
    user_id,
    selected_level,
    lc.start_time as level_choice_ts,
    pur.start_time as purchase_ts,
    (pur.start_time - lc.start_time) as time_diff
from
    events_2017 as lc
    inner join
    purchases_2017 as pur
    using(user_id)
    where lc.event_type='level_choice'
limit 20;
""")
ret = cursor.fetchall()

# И это немножко замороченное выражение печатает пример данных после фильтрации и объединения
# Проще было преобразовать результаты запроса  в датафрейм и напечатать средствами Pandas.
print("{0:8s} {1:8s} {2:23s} {3:23s} {4:20s}\n{5}".format(
        "User ID", "Level", "Lvl choice time", "Purchase time", "Interval", '-'*85
     ))
print('\n'.join(['\t'.join([str(f) for f in l]) for l in ret]))
```

Выражение, которое выбирает данные, построено, осталось их сгруппировать и посчитать
средние значения.

```
cursor.execute(curr_cte + """
select lc.selected_level,  avg(pur.start_time - lc.start_time) as avg_time_diff
from
    events_2017 as lc
    inner join
    purchases_2017 as pur
    using(user_id)
where event_type='level_choice'
group by selected_level
order by avg_time_diff;
""")
ret = cursor.fetchall()

avg_intervals_by_lvl = pd.DataFrame.from_records(ret, columns=('Level', 'Avg. Interval'), index='Level')
print(avg_intervals_by_lvl)
```

Мы видим, что в среднем покупатель, выбравший уровень _medium_, думает над покупкой на 16 часов дольше,
чем выбравший уровень _hard_, а покупатели уровня _easy_ занимают промежуточное положение.

Среднее даёт нам ограниченную информацию, было бы интереснее сравнить распределение интервалов между
выбором уровня и покупкой для разных уровней.  Для этого вспомним, что покупателей не так уж и много,
и сделаем выборку данных в таблице "уровень-интервал" для каждого из них.
Практически это предыдущий запрос, но без группировки.

```
cursor.execute(curr_cte + """
select lc.selected_level,  (pur.start_time - lc.start_time) as avg_time_diff
from
    events_2017 as lc
    inner join
    purchases_2017 as pur
    using(user_id)
where event_type='level_choice';
""")

ret = cursor.fetchall()

tdiff_by_lvl = pd.DataFrame.from_records(ret, columns=('level', 'tdiff'))
tdiff_by_lvl.loc[:,'level'] = tdiff_by_lvl.level.astype('category')
print(tdiff_by_lvl.info())
```

Если бы данных было действительно много, можно было бы расчитать в СУБД персентили с интервалом, например, 5%,
и построить график по ним.

Данные собраны, осталось их визуализировать.  Тут есть сложности, потому что тип данных `timedelta64[ns]`
не совсем числовой.

На [StackOverflow](https://stackoverflow.com/questions/23543909/plotting-pandas-timedelta) подсказывают,
что можно преобразовать интервалы в какую-нибудь единицу времени.  Нам здесь не надо очень дробно, часов
вполне достаточно:

```
tdiff_by_lvl[tdiff_by_lvl.level == 'hard'].tdiff.astype('timedelta64[h]').plot.hist()

td = tdiff_by_lvl
td.loc[:,'tdiff'] = td.tdiff.astype('timedelta64[h]')
td.plot.box(by='level')
```
