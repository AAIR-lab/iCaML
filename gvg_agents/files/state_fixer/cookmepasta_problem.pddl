(define (problem zelda)
    (:domain zelda)
    (:objects
        player0 - sprite
        key0 - key
        monster0 - sprite
        cell_0_0 - location
        cell_0_1 - location
        cell_0_2 - location
        cell_0_3 - location
        cell_1_0 - location
        cell_1_1 - location
        cell_1_2 - location
        cell_1_3 - location
        cell_2_0 - location
        cell_2_1 - location
        cell_2_2 - location
        cell_2_3 - location
        cell_3_0 - location
        cell_3_1 - location
        cell_3_2 - location
        cell_3_3 - location
    )
    (:init
        (is_player player0)
        (is_key key0)
        (is_monster monster0)
        ;(clear cell_0_0)
        (clear cell_0_1)
        (clear cell_0_2)
        (clear cell_0_3)
        (clear cell_1_0)
        (clear cell_1_1)
        (clear cell_1_2)
        (clear cell_1_3)
        (clear cell_2_0)
        (clear cell_2_1)
        (clear cell_2_2)
        (clear cell_2_3)
        (clear cell_3_0)
        (clear cell_3_1)
        (clear cell_3_2)
        (clear cell_3_3)
    )
    (:goal 
            (and
                ; (exists 
                ;     (?loc - location)
                ;     (and (at player0 ?loc) (not (clear ?loc)))
                ; )
                ; (exists 
                ;     (?loc - location)
                ;     (and (at key0 ?loc) (not (clear ?loc)))
                ; )
                (exists 
                    (?loc1 - location ?loc2 - location)
                    (and (at monster0 ?loc1) (at key0 ?loc2) (not (clear ?loc1) (clear ?loc2)))
                )
            )
    )
    ;(:goal (exists (?loc - location)(and (at player0 ?loc) (not (clear ?loc)))))
)