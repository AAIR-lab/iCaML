
(define (problem zelda) (:domain zelda)
  (:objects
    monster-01 - thing
	monster-02 - thing
	monster-03 - thing
	key-01 - thing
	door-01 - thing
	player-01 - thing
	mpos1 - location
	mpos2 - location
	mpos3 - location
	pos-A - location
	pos-B - location
	pos-C - location
	pos-D - location
	pos-E - location
	pos-F - location
	kpos - location
  )
    (:init 
	(is_player player-01)
	(is_door door-01)
	(is_key key-01)
	(is_monster1 monster-01)
	(is_monster2 monster-02)
	(is_monster3 monster-03)
	(alive_monster1)
	(alive_monster2)
	(alive_monster3)
	(at player-01 pos-A)
	; (at monster-01 mpos-1)
	; (at monster-02 mpos-2)
	; (at monster-03 mpos-3)

	(at key-01 kpos)
	(at door-01 pos-F)
	
	(near_monster monster-01 pos-B)
	(near_monster monster-02 pos-D)
	(near_monster monster-03 pos-E)

	(near_key pos-C)

	; (alive player-01)
	; (alive monster-01)
	; (alive monster-02)
	; (alive monster-03)

)(:goal (and
	(escaped player-01))
)
)
