(define (domain zelda)
    (:requirements :strips :typing :adl :existential-preconditions)
    (:types  sprite - object
             location - object)
    (:predicates (at ?x - object ?loc - location )
                (monster_alive ?obj - sprite)
                (has_key )
                (escaped )
    	        (is_player ?obj - sprite)
    	        (is_monster ?obj - sprite)
                (is_key ?obj - sprite)
                (is_door ?obj - sprite)
                (next_to_monster )
                (clear ?loc - location)
                (above ?loc1 - location ?loc2 - location)
                (below ?loc1 - location ?loc2 - location)
                (leftOf ?loc1 - location ?loc2 - location)
                (rightOf ?loc1 - location ?loc2 - location)
                (wall ?loc - location)
                (assigned ?loc - location))

    (:action add_player
        :parameters (?obj - sprite ?loc - location)
        :precondition (and (clear ?loc) (is_player ?obj))
        :effect (and (at ?obj ?loc) (assigned ?loc)
                 (not (clear ?loc))))
    
    (:action add_player_next_to_monster
        :parameters (?p - sprite ?m - sprite ?ploc - location ?mloc - location)
        :precondition (and (clear ?ploc) (is_player ?p) (is_monster ?m) (at ?m ?mloc)(or 
        (above ?ploc ?mloc) (below ?ploc ?mloc) (leftOf ?ploc ?mloc) (rightOf ?ploc ?mloc)))
        :effect (and (at ?p ?ploc) (next_to_monster )
                 (not (clear ?ploc))))
    
    (:action add_key
        :parameters (?obj - sprite ?loc - location)
        :precondition (and (clear ?loc) (is_key ?obj) (not (assigned ?loc)))
        :effect (and (at ?obj ?loc) (assigned ?loc)
                 (not (clear ?loc))))


    (:action add_door
        :parameters (?obj - sprite ?loc - location)
        :precondition (and (clear ?loc) (is_door ?obj) (not (assigned ?loc)))
        :effect (and (at ?obj ?loc) (assigned ?loc)))
    

    (:action add_monster
        :parameters (?obj - sprite ?loc - location)
        :precondition (and (clear ?loc) (is_monster ?obj))
        :effect (and (at ?obj ?loc) (monster_alive ?obj)
                 (not (clear ?loc))))
    
    (:action add_wall
        :parameters (?loc - location)
        :precondition (and (clear ?loc))
        :effect (and (wall ?loc)
                 (not (clear ?loc))))
    
    (:action add_has_key
        :parameters (?obj - sprite ?loc - location)
        :precondition (and (at ?obj ?loc) (is_key ?obj))
        :effect (and (has_key )
                     (clear ?loc)
                 (not (at ?obj ?loc))))
    
    ; (:action remove_monster
    ;     :parameters (?obj - monster ?loc - location)
    ;     :precondition (and (at ?obj ?loc))
    ;     :effect (and (clear ?loc))
    ; )
    
    (:action add_clear
        :parameters (?loc - location ?m - sprite, ?p - sprite)
        :precondition (not (at ?)
                            )
        :effect (and (has_key )
                     (clear ?loc)
                 (not (at ?obj ?loc))))
    

    (:action add_escape
         :parameters (?ploc - location ?d - sprite ?dloc - location ?p - sprite ?m - sprite ?mloc - location)
         :precondition (and (at ?d ?dloc) (has_key ) (at ?p ?ploc) (is_player ?p)
                            (is_door ?d) (is_monster ?m) (at ?m ?mloc)
                            ; (not (exists (?m - sprite ?mloc - location)
                            ;             (and (at ?m ?mloc) (is_monster ?m)
                            ;             (monster_alive ?m))
                            ;     )
                            ; )
                        )
         :effect (and (escaped )(clear ?ploc)(at ?p ?dloc)(not (at ?m ?mloc)))
    )
    
)      