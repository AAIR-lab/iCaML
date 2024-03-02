(define (problem zelda)
    (:domain zelda)
   (:objects
       cell_0_0 - location
       cell_0_1 - location
       cell_0_2 - location
       cell_0_3 - location
       cell_0_4 - location
       cell_1_0 - location
       cell_1_1 - location
       cell_1_2 - location
       cell_1_3 - location
       cell_1_4 - location
       cell_2_0 - location
       cell_2_1 - location
       cell_2_2 - location
       cell_2_3 - location
       cell_2_4 - location
       cell_3_0 - location
       cell_3_1 - location
       cell_3_2 - location
       cell_3_3 - location
       cell_3_4 - location
       cell_4_0 - location
       cell_4_1 - location
       cell_4_2 - location
       cell_4_3 - location
       cell_4_4 - location
       player0 - sprite
       key0 - sprite
       monster_0_4 - sprite
       door0 - sprite
           )
    (:init
          (is_player player0)
          (is_monster monster_0_4)
          (is_key key0)
          (is_door door0)
          (leftOf cell_0_0 cell_1_0)
          (leftOf cell_0_1 cell_1_1)
          (leftOf cell_0_2 cell_1_2)
          (leftOf cell_0_3 cell_1_3)
          (leftOf cell_0_4 cell_1_4)
          (leftOf cell_1_0 cell_2_0)
          (leftOf cell_1_1 cell_2_1)
          (leftOf cell_1_2 cell_2_2)
          (leftOf cell_1_3 cell_2_3)
          (leftOf cell_1_4 cell_2_4)
          (leftOf cell_2_0 cell_3_0)
          (leftOf cell_2_1 cell_3_1)
          (leftOf cell_2_2 cell_3_2)
          (leftOf cell_2_3 cell_3_3)
          (leftOf cell_2_4 cell_3_4)
          (leftOf cell_3_0 cell_4_0)
          (leftOf cell_3_1 cell_4_1)
          (leftOf cell_3_2 cell_4_2)
          (leftOf cell_3_3 cell_4_3)
          (leftOf cell_3_4 cell_4_4)
          (rightOf cell_1_0 cell_0_0)
          (rightOf cell_1_1 cell_0_1)
          (rightOf cell_1_2 cell_0_2)
          (rightOf cell_1_3 cell_0_3)
          (rightOf cell_1_4 cell_0_4)
          (rightOf cell_2_0 cell_1_0)
          (rightOf cell_2_1 cell_1_1)
          (rightOf cell_2_2 cell_1_2)
          (rightOf cell_2_3 cell_1_3)
          (rightOf cell_2_4 cell_1_4)
          (rightOf cell_3_0 cell_2_0)
          (rightOf cell_3_1 cell_2_1)
          (rightOf cell_3_2 cell_2_2)
          (rightOf cell_3_3 cell_2_3)
          (rightOf cell_3_4 cell_2_4)
          (rightOf cell_4_0 cell_3_0)
          (rightOf cell_4_1 cell_3_1)
          (rightOf cell_4_2 cell_3_2)
          (rightOf cell_4_3 cell_3_3)
          (rightOf cell_4_4 cell_3_4)
          (above cell_0_0 cell_0_1)
          (above cell_0_1 cell_0_2)
          (above cell_0_2 cell_0_3)
          (above cell_0_3 cell_0_4)
          (above cell_1_0 cell_1_1)
          (above cell_1_1 cell_1_2)
          (above cell_1_2 cell_1_3)
          (above cell_1_3 cell_1_4)
          (above cell_2_0 cell_2_1)
          (above cell_2_1 cell_2_2)
          (above cell_2_2 cell_2_3)
          (above cell_2_3 cell_2_4)
          (above cell_3_0 cell_3_1)
          (above cell_3_1 cell_3_2)
          (above cell_3_2 cell_3_3)
          (above cell_3_3 cell_3_4)
          (above cell_4_0 cell_4_1)
          (above cell_4_1 cell_4_2)
          (above cell_4_2 cell_4_3)
          (above cell_4_3 cell_4_4)
          (below cell_0_1 cell_0_0)
          (below cell_0_2 cell_0_1)
          (below cell_0_3 cell_0_2)
          (below cell_0_4 cell_0_3)
          (below cell_1_1 cell_1_0)
          (below cell_1_2 cell_1_1)
          (below cell_1_3 cell_1_2)
          (below cell_1_4 cell_1_3)
          (below cell_2_1 cell_2_0)
          (below cell_2_2 cell_2_1)
          (below cell_2_3 cell_2_2)
          (below cell_2_4 cell_2_3)
          (below cell_3_1 cell_3_0)
          (below cell_3_2 cell_3_1)
          (below cell_3_3 cell_3_2)
          (below cell_3_4 cell_3_3)
          (below cell_4_1 cell_4_0)
          (below cell_4_2 cell_4_1)
          (below cell_4_3 cell_4_2)
          (below cell_4_4 cell_4_3)
          (clear cell_0_0)
          (clear cell_0_1)
          (clear cell_0_2)
          (clear cell_0_3)
          (clear cell_0_4)
          (clear cell_1_0)
          (clear cell_1_1)
          (clear cell_1_2)
          (clear cell_1_3)
          (clear cell_1_4)
          (clear cell_2_0)
          (clear cell_2_1)
          (clear cell_2_2)
          (clear cell_2_3)
          (clear cell_2_4)
          (clear cell_3_0)
          (clear cell_3_1)
          (clear cell_3_2)
          (clear cell_3_3)
          (clear cell_3_4)
          (clear cell_4_0)
          (clear cell_4_1)
          (clear cell_4_2)
          (clear cell_4_3)
          (clear cell_4_4)
          )
    (:goal (and
          (and 
                (exists 
                    (?loc1 - location ?loc2 - location)
                    (and
                        (at player0 ?loc1) 
                        (at door0 ?loc2)
                    )
                ) 
                (or
                    (has_key )
                    (exists 
                        (?loc2 - location)
                        (at key0 ?loc2)
                    
                    )
                )
                (not (at player0 cell_0_1))
          )            )
   )
)