# Взаимосвязь прохождения обучения и покупки тренировок

## Разбиение пользователей на группы

### Прошли обучение

> Сначала определим пользователей, которые прошли обучение хотя бы раз

Это такие пользователи, у которых есть хотя бы одно событие `tutorial_finish`.

Эти пользователи получаются из базы селектом:

```
select distinct user_id from evts17 where event_type='tutorial_finish'
```

Мы уже знаем, что таких пользователей 10250.

### Начали обучение, но не прошли его ни разу.

У этих пользователей есть событие `tutorial_start`, но нет события `tutorial_finish`;

Как получается такая выборка?

```
select distinct user_id from evts17 where event_type='tutorial_start'                      
except                                                               
select distinct user_id from evts17 where event_type='tutorial_finish'   
limit 5;

 user_id 
---------
   39224
   37083
   34261
   33957
   37922
```

И сколько таких пользователей?

```
select count (user_id) from 
(select distinct user_id from evts17 where event_type='tutorial_start'
except
select distinct user_id from evts17 where event_type='tutorial_finish'
) as t;

 count 
-------
  1608
```

### Не начинали обучение вовсе

> последняя группа пользователей — те, кто ни разу не проходил обучение, а сразу же перешел к выбору уровня сложности тренировок.
> У таких пользователей отсутствует событие `tutorial_start`.

Замечу, что в большинстве своём это будет пользователи, которые зарегистрировались и ничего больше не делали.

```
select distinct user_id from evts17
except
select distinct user_id from evts17 where event_type='tutorial_start'
limit 5;

user_id 
---------
   47051
   35634
   40694
   28031
   42422
```

И таких пользователей... 

```
dgolub=> select count(u.user_id) from (select distinct user_id from evts17
except
select distinct user_id from evts17 where event_type='tutorial_start') as u
;
 count 
-------
  8068
```

Проверяем, что сумма сошлась.  Это надо бы бы по-хорошему переписать.

```
select 'Registered:' as type, count(distinct user_id) as count from evts17 
union all
select 'Finished Tutorial', count(distinct user_id) from evts17 where event_type='tutorial_finish'
union all
select 'Not finished tutorial', count(user_id) from (
select distinct user_id from evts17 where event_type='tutorial_start'
except
select distinct user_id from evts17 where event_type='tutorial_finish'
) as ts
union all
select 'Not started tutorial', count(user_id) as nots_count from (
select distinct user_id from evts17
except
select distinct user_id from evts17 where event_type='tutorial_start'
) as nots
;
         type          | count 
-----------------------+-------
 Registered:           | 19926
 Finished Tutorial     | 10250
 Not finished tutorial |  1608
 Not started tutorial  |  8068
```

Выражения получаются громоздкие, создам представления для каждого из вариантов:

```
dgolub=> create view c8_finished_tutorial as
dgolub-> select distinct user_id from evts17 where event_type='tutorial_finish';
CREATE VIEW

dgolub=> create view c8_started_tutorial as
dgolub-> select distinct user_id from evts17 where event_type='tutorial_start'
dgolub-> except
dgolub-> select distinct user_id from evts17 where event_type='tutorial_finish';
CREATE VIEW

dgolub=> create view c8_not_started_tutorial as
dgolub-> select distinct user_id from evts17
dgolub-> except
dgolub-> select distinct user_id from evts17 where event_type='tutorial_start';
CREATE VIEW
```

## Определение конверсии пользователей в покупателей по группам

Базовый запрос при поиске конверсии и среднего чека будет выглядеть примерно так. Для подсчёта числа покупателей достаточно
сосчитать значения в колонке 'id', или 'amount', или 'start_time'.

```
select * from
c8_finished_tutorial
left join
purs17
using(user_id)
limit 40;

 user_id |     start_time      | amount |  id
---------+---------------------+--------+-------
   44127 |                     |        |
   ..........
   37878 | 2017-06-30 17:05:21 |    150 | 17668
   47216 | 2017-12-22 06:30:31 |     25 | 18396
   35532 | 2017-05-21 04:23:32 |    150 | 17475
   41011 |                     |        |
```

### Группа закончивших обучение:

Конверсия:

```
dgolub=> select round(count(id)*100.0/count(user_id),1) from
c8_finished_tutorial
left join
purs17
using(user_id);
 round 
-------
  14.1
```

Средний чек:

```
dgolub=> select round(avg(amount), 2) 
from c8_finished_tutorial
left join
purs17
using(user_id);

 round  
--------
 110.99
```

Итак, в группе закончивших обучение конверсия 14.1% и средний чек 110 р.

### Группа начавших обучение

Совершенно аналогично:

```
dgolub=> select round(count(id)*100.0/count(user_id),1) from
c8_started_tutorial
left join
purs17
using(user_id);
 round 
-------
   8.1

dgolub=> select round(avg(amount), 2) from c8_started_tutorial
left join
purs17
using(user_id);
 round  
--------
 104.96
```

В группе начавших обучение конверсия 8.1% и средний чек 104 р.

### Группа не начнавших обучение

```
dgolub=> select round(count(id)*100.0/count(user_id),1) from
c8_not_started_tutorial
left join
purs17
using(user_id);
 round 
-------
   0.3

dgolub=> select round(avg(amount), 2) from c8_not_started_tutorial
left join
purs17
using(user_id);
 round  
--------
 128.41
```

Эта группа с очень маленькой конверсией (0.3%), но средний чек заметно выше, чем в первых двух группах.

#### Подгруппа: не начинавшие обучение, но сразу выбравшие уровень сложности

Для упрощения выражений тоже создам представление, назову его `c8_hurried_users`:

```
create view c8_hurried_users as
select user_id 
from 
    c8_not_started_tutorial
    join
    evts17  
    using (user_id)
where event_type='level_choice';
```

При запуске этого запроса получаем:

```
CREATE VIEW

dgolub=> select count(*) from c8_hurried_users;
 count 
-------
    98
```

Из схем переходов выше мы знаем, что именно это число пользователей выбрало уровень сложности сразу после регистрации.

Посчитаем конверсию в этой подгруппе:

```
select round(count(id)*100.0/count(user_id),1)
from
    c8_hurried_users
    left join
    purs17
    using(user_id);
```

При запуске получаем:

```
round 
-------
  22.4
```

И средний чек мы уже знаем:

```
dgolub=> select round(avg(amount),2)
from
    c8_hurried_users
    left join
    purs17
    using(user_id);
 round  
--------
 128.41
```

Итак, получили подгруппу с аномально высокой конверсией (22.4%) и высоким средним чеком.  Могу предположить, что это пользователи,
повторно устанавливающие приложение, например, после ремонта устройства.  В обучении они уже не нуждаются, знают, чего хотят, и 
готовы за это платить.  Было бы полезно обратить внимание на эту подгруппу пользователей.

Возможно, есть смысл предусмотреть в приложении возможность сохранения состояния в «облако» и его восстановления.

### Итоги изучения конверсии и среднего чека по группам

Подсчёты конверсии и среднего чека по разным группам пользователей подтверждают, что прохождение обучения до конца благотворно
влияет на желание пользователя оплачивать тренировки.

|  Группа пользователей                             |  Конвесия %   | Средний чек |
|:--------------------------------------------------|--------------:|------------:|
| Не проходили обучение                             |       0.3     |     128.41  |
| Начали обучение, но не закончили                  |       8.1     |     105     |
| Закончили обучение                                |      14.1     |     111     |
