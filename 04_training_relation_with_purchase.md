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


