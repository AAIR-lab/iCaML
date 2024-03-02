(define (domain cookmepasta)
    (:requirements :strips :typing :adl :conditional-effects :existential-preconditions)
    (:types sprite - object
            location - object
            player - sprite
            raw_pasta - sprite
            pasta - sprite
            tomato - sprite
            tuna - sprite
            pasta_in_place - sprite
            sauce_in_place - sprite
            pasta_done - sprite
    )
    (:predicates (at ?x - sprite ?loc - location )
                (clear ?loc - location)
                (pasta_cooked )
                (above ?loc1 - location ?loc2 - location)
                (below ?loc1 - location ?loc2 - location)
                (leftOf ?loc1 - location ?loc2 - location)
                (rightOf ?loc1 - location ?loc2 - location)
                (wall ?loc)
    )

    (:action add_sprite
        :parameters (?obj - sprite ?loc - location)
        :precondition (and (clear ?loc) (is_player ?obj))
        :effect (and (at ?obj ?loc)
                 (not (clear ?loc))
                (when
                    (and (?obj - pasta_done))
                    (pasta_cooked )
                )               
                )
    )    
    (:action add_wall
        :parameters (?loc - location)
        :precondition (and (clear ?loc))
        :effect (and (wall ?loc)
                 (not (clear ?loc)))
    )
    
)
             