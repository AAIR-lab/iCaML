(define (domain escape)
    (:requirements :strips :typing :adl :conditional-effects :existential-preconditions)
    (:types 
            sprite - object
            location - object
            player - sprite
            block - sprite
    )
    (:predicates (at ?x - sprite ?loc - location)
                (clear ?loc - location)
                (escape )
                (is_door ?loc - location)
                (is_hole ?loc - location)
                (above ?loc1 - location ?loc2 - location)
                (below ?loc1 - location ?loc2 - location)
                (leftOf ?loc1 - location ?loc2 - location)
                (rightOf ?loc1 - location ?loc2 - location)
                (wall ?loc))

    (:action add_player
        :parameters (?obj - sprite ?loc - location)
        :precondition (and (clear ?loc) (is_player ?obj))
        :effect (and (at ?obj ?loc)
                 (not (clear ?loc))               
                )
    )    
    (:action add_hole
        :parameters (?obj - sprite ?loc - location)
        :precondition (and (clear ?loc) (is_player ?obj))
        :effect (and (at ?obj ?loc)
                 (not (clear ?loc))               
                )

    )

    (:action add_door
        :parameters (?obj - sprite ?loc - location)
        :precondition (and (clear ?loc) (is_player ?obj))
        :effect (and (at ?obj ?loc)
                 (not (clear ?loc))               
                )
    )

    (:action add_wall
        :parameters (?loc - location)
        :precondition (and (clear ?loc))
        :effect (and (wall ?loc)
                 (not (clear ?loc)))
    )
    
)
             