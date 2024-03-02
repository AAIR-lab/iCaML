(define (domain zelda)
  (:requirements :typing :negative-preconditions)
  (:types thing location)
  (:predicates (at ?v0 - thing ?cell - location)
	;(near_monster ?monster - thing ?cell - location)
    ;(near_key ?cell - location)
    (alive ?thing - thing)
    (has_key ?player - thing)
    (door_at ?cell - location)
    (escaped ?player - thing)
    (clear ?cell - location)
	(is_player ?item - thing)
	(is_key ?item - thing)
	(is_door ?item - thing)
	(is_monster1 ?monster - thing)
	(is_monster2 ?monster - thing)
	(is_monster3 ?monster - thing)
	;(is_monster ?item - thing)
	; (connected ?cell1 ?cell2)
	(alive_monster1)
	(alive_monster2)
	(alive_monster3)
  )

  	(:action move
		:parameters (?player - thing ?from - location ?to - location)
		:precondition (and (at ?player ?from)
		(is_player ?player)
		)
		:effect (and
			(not (at ?player ?from))
			(at ?player ?to))
	)

	(:action kill_monster1
		:parameters (?player - thing ?monster - thing ?pcell - location)
		:precondition (and (near_monster ?monster ?pcell)
			(at ?player ?pcell)
			(alive_monster1)
			(is_player ?player)
			(is_monster1 ?monster))
		:effect (and
			(not (alive_monster1))
			(not(near_monster ?monster ?pcell)))
	)
	
	(:action kill_monster2
		:parameters (?player - thing ?monster - thing ?pcell - location)
		:precondition (and (near_monster ?monster ?pcell)
			(at ?player ?pcell)
			; (alive ?monster)
			(alive_monster2)
			(is_player ?player)
			(is_monster2 ?monster))
		:effect (and
			(not (alive_monster2))
			(not(near_monster ?monster ?pcell)))
	)
	
	(:action kill_monster3
		:parameters (?player - thing ?monster - thing ?pcell - location)
		:precondition (and (near_monster ?monster ?pcell)
			(at ?player ?pcell)
			(alive_monster3)
			(is_player ?player)
			(is_monster3 ?monster))
		:effect (and
			(not (alive_monster3))
			(not(near_monster ?monster ?pcell)))
	)

	(:action get_key
		:parameters (?player - thing ?ploc - location ?kloc - location ?key - thing)
		:precondition (and 
        (at ?player ?ploc)
        (at ?key ?kloc)
		(is_player ?player)
        (near_key ?ploc)
        (not(has_key ?player))
		(is_key ?key)
        )
		:effect (and
			(not (at ?player ?ploc))
            (at ?player ?kloc)
			(has_key ?player)
			(not(near_key ?kloc))
			)
	)

    (:action escape
		:parameters (?player - thing ?ploc - location  ?door - thing)
		:precondition (and 
        (at ?player ?ploc)
		(is_door ?door)
		(has_key ?player)
		(is_player ?player)
        (at ?door ?ploc)
        (not (alive_monster1))
		(not (alive_monster2))
		(not (alive_monster3))
        )
		:effect (and
			(escaped ?player)
			)
	)

)