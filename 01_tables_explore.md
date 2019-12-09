# Анализ пользовательских событий (повторяю рассуждения из учебника, но использую по возможности SQL вместо Python).

Мотивация такого подхода: конечно, всё можно загрузить в Pandas и пользоваться его методами.  Но ресурсы компьютера обычно
ограничены, а тут у нас есть под рукой целая база данных, которая какие надо выборки и сортировки великолепно делает.

> Сколько строк содержится в датафрейме events_df? (для ответа используйте данные за 2017 год)

```
dgolub=> select count(e.id)
from case8.events as e
where user_id in (select distinct user_id from case8.events where event_type='registration' and start_time between '2017-01-01' and '2018-01-01');
 count
-------
 66959
(1 row) 
```

> Сколько непустых значений содержится в столбце selected_level? (для ответа используйте данные за 2017 год)

```
dgolub=> select count(e.selected_level)
from case8.events as e
where user_id in (select distinct user_id from case8.events where event_type='registration' and start_time between '2017-01-01' and '2018-01-01');
 count 
-------
 8342
(1 row)
```

Аналогично можно поступить с CTE:

```
dgolub=> with all_users as (
    SELECT DISTINCT user_id
    FROM case8.events
    WHERE event_type = 'registration'
    AND start_time BETWEEN '2017-01-01' AND '2018-01-01'
)
select count(e.selected_level) from case8.events as e join all_users as u using (user_id);
 count 
-------
  8342

dgolub=> with all_users as (
    SELECT DISTINCT user_id
    FROM case8.events
    WHERE event_type = 'registration'
    AND start_time BETWEEN '2017-01-01' AND '2018-01-01'
)
select count(*) from case8.events as e join all_users as u using (user_id);
 count 
-------
 66959
```

Для удобства создал представление `evts17`, в котором только пользователи, зарегистрированные в 2017 году.

```
create view evts17 as
    select * from case8.events
    where user_id in
        (select distinct user_id from case8.events 
         where event_type='registration' 
         and 
         start_time between '2017-01-01' and '2018-01-01'
        );
CREATE VIEW

dgolub=> select count(*) from evts17;
 count 
-------
 66959
```

Аналогично создал представление purs17, где покупки, совершённые зарегистрированными в 2017 пользователями:

```
create view purs17 as
select * from case8.purchase
where user_id in (
   select distinct user_id 
   from case8.events 
   where 
      event_type='registration' 
      and 
      start_time between '2017-01-01' and '2018-01-01'
); 

dgolub=> select count(*) from purs17;
 count 
 -------
 1600
```

Структура представления повторяет соответствующие таблицы (в представление выбраны все колонки):

```
dgolub=> \d evts17
                             View "public.evts17"
     Column     |            Type             | Collation | Nullable | Default 
----------------+-----------------------------+-----------+----------+---------
 event_type     | text                        |           |          | 
 selected_level | text                        |           |          | 
 start_time     | timestamp without time zone |           |          | 
 tutorial_id    | integer                     |           |          | 
 user_id        | integer                     |           |          | 
 id             | integer                     |           |          |

dgolub=> \d purs17
                           View "public.purs17"
   Column   |            Type             | Collation | Nullable | Default 
------------+-----------------------------+-----------+----------+---------
 user_id    | integer                     |           |          | 
 start_time | timestamp without time zone |           |          | 
 amount     | integer                     |           |          | 
 id         | integer                     |           |          | 

```

> К примеру, посмотрим на `events_df`, если оставить в нем только такие строки, где event_type = level_choice:

```
dgolub=> select 
        count(event_type) c_evtype,
        count(selected_level) as c_sellvl,
        count(start_time) as c_starttm,
        count(tutorial_id) as c_tut_id,
        count(user_id) as c_usr_id,
        count(id) as c_id
    from evts17 
    where event_type='level_choice';


 c_evtype | c_sellvl | c_starttm | c_tut_id | c_usr_id | c_id 
----------+----------+-----------+----------+----------+------
     8342 |     8342 |      8342 |        0 |     8342 | 8342     
```

> Как видно, этот срез датафрейма не содержит пропущенных значений в столбце `selected_level`,
> но зато содержит пропуски в `tutorial_id`. Это связано с тем, что для событий типа level_choice
> не предусмотрена запись параметра `tutorial_id`.
 
> Теперь проверим аналогичные данные, но при условии, что срез будет содержать
> данные о событиях `tutorial_start` и `tutorial_finish`.

```
dgolub=> select 
  count(event_type) c_evtype, 
  count(selected_level) c_sellvl, 
  count(start_time) c_starttm, 
  count (tutorial_id) c_tut_id, 
  count(user_id) c_usr_id, 
  count(id) c_id 
from evts17 
where event_type in ('tutorial_finish', 'tutorial_start');

 c_evtype | c_sellvl | c_starttm | c_tut_id | c_usr_id | c_id  
----------+----------+-----------+----------+----------+-------
    32954 |        0 |     32954 |    32954 |    32954 | 32954
```

> Давайте оценим, какие уникальные события есть в колонках `event_type` и `selected_level`:

```
dgolub=> select distinct event_type from evts17;

   event_type    
-----------------
 training_choice
 tutorial_finish
 level_choice
 tutorial_start
 registration
 
dgolub=> select distinct selected_level from evts17;
 selected_level 
----------------
 hard
 medium
 
 easy
```

Обращаю внимание: во второй выдаче есть пропуск (NULL).  Но везде, где событие = `level_choice` , поле `selected_level` заполнено:

```
dgolub=> select distinct selected_level from evts17 where event_type='level_choice';
 selected_level 
----------------
 hard
 medium
 easy
```

> Также оценим, какое количество пользователей совершали события:
> ...
> Сколько уникальных пользователей совершали события в датафрейме `events_df`? 
> (для ответа используйте данные за 2017 год)

```
dgolub=> select count(distinct user_id) from evts17;
 count 
-------
 19926
```

Кстати, посмотрю сразу и покупки -- количество покупателей и количество покупок:

```
dgolub=> select count(distinct user_id) from purs17;
 count 
-------
  1600

dgolub=> select count(*) from purs17;
 count 
-------
  1600
```

Никаких других данных, кроме покупок, в представлении `purs17` не содержится, пользователи покупают
тренировки (когда покупают) по одному разу.

> Есть ли пропущенные значения в датафрейме `purchase_df`?

```
dgolub=> select count(user_id) c_uid, count(start_time) c_time, count(amount) as c_amt, count(id) as c_id from purs17;
 c_uid | c_time | c_amt | c_id 
-------+--------+-------+------
  1600 |   1600 |  1600 | 1600
```

> Снова обратимся к методу `describe()` для того, чтобы оценить характеристики каждого столбца датафрейма `purchase_df`

Каждый столбец нам тут совершенно не нужен, к тому же `user_id` и `id`, хоть и как бы числовые значения, но на самом деле
просто идентификаторы.  А вот содержимое колонки `amount` стоит посмотреть:

```
dgolub=> select round(avg(amount),2) as avg_amount from purs17;

 avg_amount 
------------
     110.73

dgolub=> select distinct amount from purs17;

 amount 
--------
    300
     25
    100
    250
    150
     50
    200
```

Поиск медианы: На сайте [leafo.net](https://leafo.net/guides/postgresql-calculating-percentile.html) описаны
функции `percentile_disc` и `percentile_cont`, которые добавлены в PostgreSQL начиная с версии 9.4.

```
dgolub=> select percentile_cont(0.5) within group (order by amount) from purs17;

 percentile_cont 
-----------------
             100
```

Персентиль 50% и есть медиана.

## Анализ событий (таблица `events`)

> Для того, чтобы понимать, как пользователи переходят из этапа в этап, на каких этапах
> возникают сложности, мы должны определить конверсию на каждом из этапов воронки. То
> есть нам нужно понять, какой процент пользователей переходит с предыдущего этапа
> на следующий.

> Посмотрим на количество пользователей, которые совершают событие *registration*

Немного дурной вопрос, мы же пользователей и ищем по событию registration.  Это будет
количество уникальных пользователей (и пользователей вообще, так как вряд ли кто-то регистрируется
более одного раза. Хотя надо проверить).

```
dgolub=> select count(distinct user_id) from evts17 where event_type='registration';
 count 
-------
 19926

dgolub=> select count(user_id) from evts17 where event_type='registration';
 count 
-------
 19926
```

Всё нормально, дважды зарегистрированных пользователей нет.

### Анализ событий `tutorial_start` и `tutorial_finish`

> Посмотрим на количество пользователей, которые совершают событие tutorial_start:

```
dgolub=> select count(id) from evts17 where event_type='tutorial_start';
 count 
-------
 18050

dgolub=> select count(distinct user_id) from evts17 where event_type='tutorial_start';
 count 
-------
 11858
```

Событий заметно больше, чем уникальных пользователей, которые их совершают.
Видимо, заметная доля пользователей начинает обучение более одного раза.

### Исследуем пользователей, перешедших к обучению

> Давайте определим процент пользователей, которые перешли к выполнению обучения

> Каков процент пользователей, начавших обучение (от общего числа
> зарегистрировавшихся)? (для ответа используйте данные за 2017 год; ответ дайте с
> округлением до двух знаков после точки-разделителя)

```
dgolub=> select round(ts.count*100.0/reg.count,2) as ts_pct
from
 (select count(distinct user_id) from evts17 where event_type='tutorial_start') as ts,
 (select count(distinct user_id) from evts17 where event_type='registration') as reg;
 ts_pct 
--------
  59.51
```

### Пользователи, завершившие обучение

> Какой процент пользователей, завершивших обучение (от числа пользователей, начавших
> обучение)? (для ответа используйте данные за 2017 год; ответ дайте с округлением до
> двух знаков после точки-разделителя)

```
dgolub=> select round(te.count*100.0/ts.count,2) as te_ts_pct
from
 (select count(distinct user_id) from evts17 where event_type='tutorial_start') as ts,
 (select count(distinct user_id) from evts17 where event_type='tutorial_finish') as te;
 
te_ts_pct 
-----------
 86.44
```

> В нашем приложении достаточно хороший процент прохождения обучения. Но есть куда
> стремиться для его увеличения. Подумайте о том, как показатель прохождения может
> влиять на весь путь пользователя в дальнейшем.

Есть закономерность, согласно которой вложенные усилия (например, в обучение) повышают шанс на то,
что и в дальнейшем будут предприниматься усилия («не можем же мы сейчас, когда столько усилий затратили,
всё бросить! Нужно затратить больше усилий!»).  Можно ожидать больших долей сделавших
выбор уровня сложности и покупателей среди прошедших тренинг пользователей.

### Анализ события level_choice

#### Количество пользователей, которые сделали выбор уровня сложности

```
dgolub=> select count(user_id) from evts17 where event_type='level_choice';
 count 
-------
8342

dgolub=> select count(distinct user_id) from evts17 where event_type='level_choice';
 count 
-------
8342
```

Прекрасно, один и тот же пользователь не выбирает уровень сложности несколько раз.  А сколько
это будет в процентах от общего числа зарегистрировавшихся?

```
select round(ls.count*100.0/reg.count,2) as ts_pct
from
 (select count(distinct user_id) from evts17 where event_type='level_choice') as ls,
 (select count(distinct user_id) from evts17 where event_type='registration') as reg;
 
ts_pct 
--------
  41.86
```

Почти 42% пользователей выбирают какой-нибудь уровень сложности.  А зависит ли это от того, прошёл ли 
пользователь обучение? Или хотя бы начинал ли его проходить?

Нужно придумать общее выражение для ситуации "доля пользователей, совершивших событие B, от пользователей, 
совершивших событие A".  На помощь приходит `LEFT JOIN`

Начнём с `tutorial_start`, посчитаем по количеству пользователей и процент:

```
select count(te.user_id) as te, count(ts.user_id) as ts 
from 
    (select distinct user_id from evts17 where event_type='tutorial_start') as ts 
    left join 
    (select distinct user_id from evts17 where event_type='level_choice') as te using (user_id); 
    
  te  |  ts   
------+-------
 8244 | 11858
(1 row)

select round(count(lc.user_id) * 100 / count(ts.user_id), 2)  as "lvl_choice%" 
from 
    (select distinct user_id from evts17 where event_type='tutorial_start') as ts 
    left join 
    (select distinct user_id from evts17 where event_type='level_choice') as lc using (user_id);

 lvl_choice% 
-------------
       69.00
(1 row)
```

Доля выбравших уровень сложности среди начавших обучение пользователей заметно выше, чем среди
всех пользователей ("валовая").  Посмотрим, поднимается ли эта доля по окончании обучения?

Для `tutorial_finish` аналогично (набрал прямо в `psql`:

```
dgolub=> select count(lc.user_id) as lc, count(tf.user_id) as tf 
from  (select distinct user_id from evts17 where event_type='tutorial_finish') as tf 
left join (select distinct user_id from evts17 where event_type='level_choice') as lc using (user_id); 

  lc  |  tf   
------+-------
 7501 | 10250

dgolub=> select round(100.0 * count(lc.user_id)  / count(tf.user_id), 2)  as "lvl_choice%" 
from (select distinct user_id from evts17 where event_type='tutorial_finish') as tf 
left join (select distinct user_id from evts17 where event_type='level_choice') as lc using (user_id); 

 lvl_choice% 
-------------
       73.18
```

Видим, что среди закончивших обучение процент выбравших уровень ещё выше. Для контроля нужно
расчитать процент пользователей, которые не проходили обучение, но выбрали уровень.

```
with 
    curious as (
        select distinct user_id from evts17 where event_type='tutorial_start'    
    ),
    ignorant as (
        select user_id from evts17 
        where event_type='registration' and user_id not in (select user_id from curious)
    ),
    ignorant_lc as (
    	select user_id from evts17
    	where event_type='level_choice' and user_id in (select user_id from ignorant)
    )
select 
    count(lc.user_id) as lvl_choice, 
    count(ignorant.user_id) as ingorants
from
   ignorant left join ignorant_lc as lc using (user_id);

 lvl_choice | ingorants 
------------+-----------
         98 |      8068
```

В процентах это чуть больше 1.2, то есть необходимо зазывать пользователей на обучение.

Ещё один возможный путь — пользователь начал обучение, но не закончил и сразу перешёл к выбору уровня
сложности.

### Анализ события training_choice

Общее число пользователей. выбравших бесплатные тренировки (`training_choice`):

```
dgolub=> select count(user_id) from evts17 where event_type='training_choice';
 count 
-------
  5737
```

И да, я проверил, что `distinct` ничего не меняет — тренировки пользователь выбирает один раз.

> Оценим процент таких пользователей от числа пользователей, которые выбрали уровень сложности:

```
select round(count(tc.user_id) * 100.0 / count(lc.user_id), 2)  as "trn_choice%" 
from 
    (select distinct user_id from evts17 where event_type='level_choice') as lc
    left join 
    (select distinct user_id from evts17 where event_type='training_choice') as tc 
    using (user_id);
    
trn_choice% 
-------------
       68.77
```

Не все доходят.  А есть ли среди пользователей этапа выбора тренировок такие, которые не выбирали уровень?

```
dgolub=> select count(distinct user_id) from evts17 where event_type='training_choice' and user_id not in (select distinct user_id from evts17 where event_type='level_choice');
 count 
-------
     0
```
ОК, таких пользователей нет.  Все пользователи, выбравшие бесплатные тренировки, сначала выбирали уровень сложности.

Проверка: замена в запросе `not in` на `in` даёт нам уже известное число пользователей, выбравших бесплатные тренировки.

## Исследование покупателей (таблица `purchase`)

> Рассчитаем процент пользователей percent_of_paying_users, которые оплатили тренировки от числа пользователей, 
> которые выбрали бесплатные тренировки:

```
select round(buyers.count*100.0/trained.count,2) as buyers_pct
from
 (select count(distinct user_id) from purs17) as buyers,
 (select count(distinct user_id) from evts17 where event_type='training_choice') as trained;
 
 buyers_pct 
------------
      27.89
```

> Какой процент пользователей, которые оплатили тренировки (от числа зарегистрировавшихся пользователей)?

```
dgolub=> select round(buyers.count*100.0/reg.count,2) as buyers_pct
from
 (select count(distinct user_id) from purs17) as buyers,
 (select count(distinct user_id) from evts17 where event_type='registration') as reg;
 buyers_pct 
------------
      8.03
```

Итак, до покупки в 2017 году доходили чуть больше 8% зарегистрированых пользователей.

А есть ли такие покупатели, которые не выбирали уровень тренировок или не проходили бесплатных тренировок:

```
dgolub=> select count(distinct user_id) from purs17 where user_id not in (select distinct user_id from evts17 where event_type='level_choice');
 count 
-------
     0

dgolub=> select count(distinct user_id) from purs17 where user_id in (select distinct user_id from evts17 where event_type='level_choice');
 count 
-------
  1600
```

Аналогично с `training_choice`:

```
dgolub=> select count(distinct user_id) from purs17 where user_id not in (select distinct user_id from evts17 where event_type='training_choice');
 count 
-------
     0

dgolub=> select count(distinct user_id) from purs17 where user_id in (select distinct user_id from evts17 where event_type='training_choice');
 count 
-------
  1600
```

Прямой ответ — таких покупателей нет.

## Выводы после анализа событий

Все данные по выборке пользователей, зарегистрированных в 2017 году.

 * Количество зарегистрировавшихся пользователей: 19926;
 * Количество пользователей, начавших обучение : 11858;
 * % пользователей, начавших обучение (от общего числа зарегистрировавшихся): 59.5;
 * Количество пользователей, завершивших обучение: 10250;
 * % пользователей, завершивших обучение (от начавших): 86.4;
 * Количество пользователей, выбравших уровень сложности: 8342;
 * % пользователей, выбравших уровень сложности тренировок (от общего числа зарегистрировавшихся): 41.9;
 * Количество пользователей, выбравших набор бесплатных тренировок: 5737;
 * % пользователей, выбравших набор бесплатных тренировок (от числа пользователей, которые выбрали уровень сложности): 68.8;
 * Количество покупателей тренировок: 1600;
 * % покупателей от числа пользователей, выбравших тренировки: 27.9;
 * % покупателей от зарегистрированных пользователей: 8.03. 
