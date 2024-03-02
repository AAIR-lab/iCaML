(define (problem minecraft) 
    (:domain minecraft)

    (:objects
    
	log-0 - moveable
	log-1 - moveable
	log-2 - moveable
	log-3 - moveable
	new-0 - moveable
	new-1 - moveable
	new-2 - moveable
	agent - agent
	loc-0-0 - static
	loc-0-1 - static
	loc-0-2 - static
	loc-1-0 - static
	loc-1-1 - static
	loc-1-2 - static
	loc-2-0 - static
	loc-2-1 - static
	loc-2-2 - static
    )

    (:init
    
	(Hypothetical new-0)
	(Hypothetical new-1)
	(Hypothetical new-2)
	(IsLog log-0)
	(IsLog log-1)
	(IsLog log-2)
	(IsLog log-3)
	(At log-0 loc-2-0)
	(At log-1 loc-0-1)
	(At log-2 loc-1-0)
	(At log-3 loc-1-1)
	(AgentAt loc-2-0)
	(Handsfree agent)

    ; Action literals
    
	(recall log-0)
	(craftplank log-0 log-1)
	(craftplank log-0 log-2)
	(craftplank log-0 log-3)
	(craftplank log-0 new-0)
	(craftplank log-0 new-1)
	(craftplank log-0 new-2)
	(equip log-0)
	(pick log-0)
	(recall log-1)
	(craftplank log-1 log-0)
	(craftplank log-1 log-2)
	(craftplank log-1 log-3)
	(craftplank log-1 new-0)
	(craftplank log-1 new-1)
	(craftplank log-1 new-2)
	(equip log-1)
	(pick log-1)
	(recall log-2)
	(craftplank log-2 log-0)
	(craftplank log-2 log-1)
	(craftplank log-2 log-3)
	(craftplank log-2 new-0)
	(craftplank log-2 new-1)
	(craftplank log-2 new-2)
	(equip log-2)
	(pick log-2)
	(recall log-3)
	(craftplank log-3 log-0)
	(craftplank log-3 log-1)
	(craftplank log-3 log-2)
	(craftplank log-3 new-0)
	(craftplank log-3 new-1)
	(craftplank log-3 new-2)
	(equip log-3)
	(pick log-3)
	(recall new-0)
	(craftplank new-0 log-0)
	(craftplank new-0 log-1)
	(craftplank new-0 log-2)
	(craftplank new-0 log-3)
	(craftplank new-0 new-1)
	(craftplank new-0 new-2)
	(equip new-0)
	(pick new-0)
	(recall new-1)
	(craftplank new-1 log-0)
	(craftplank new-1 log-1)
	(craftplank new-1 log-2)
	(craftplank new-1 log-3)
	(craftplank new-1 new-0)
	(craftplank new-1 new-2)
	(equip new-1)
	(pick new-1)
	(recall new-2)
	(craftplank new-2 log-0)
	(craftplank new-2 log-1)
	(craftplank new-2 log-2)
	(craftplank new-2 log-3)
	(craftplank new-2 new-0)
	(craftplank new-2 new-1)
	(equip new-2)
	(pick new-2)
	(move loc-0-0)
	(move loc-0-1)
	(move loc-0-2)
	(move loc-1-0)
	(move loc-1-1)
	(move loc-1-2)
	(move loc-2-0)
	(move loc-2-1)
	(move loc-2-2)
    )

    (:goal (and  (Inventory new-2) ))
)
    