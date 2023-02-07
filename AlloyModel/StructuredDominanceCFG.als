/*
     █████████  ███████████  █████ ███████████              █████   █████
    ███░░░░░███░░███░░░░░███░░███ ░░███░░░░░███            ░░███   ░░███
   ░███    ░░░  ░███    ░███ ░███  ░███    ░███             ░███    ░███
   ░░█████████  ░██████████  ░███  ░██████████   ██████████ ░███    ░███
    ░░░░░░░░███ ░███░░░░░░   ░███  ░███░░░░░███ ░░░░░░░░░░  ░░███   ███
    ███    ░███ ░███         ░███  ░███    ░███              ░░░█████░
   ░░█████████  █████        █████ █████   █████               ░░███
    ░░░░░░░░░  ░░░░░        ░░░░░ ░░░░░   ░░░░░                 ░░░


  ┌─┐┬  ┬    ┌─┐┬ ┬┌┐┌┌─┐┌┬┐┬┌─┐┌┐┌'┌─┐  ┬  ┌─┐┌─┐┌─┐┌─┐  ┌─┐┬─┐┌─┐  ┌─┐┌┬┐┬─┐┬ ┬┌─┐┌┬┐┬ ┬┬─┐┌─┐┌┬┐
  ├─┤│  │    ├┤ │ │││││   │ ││ ││││ └─┐  │  │ ││ │├─┘└─┐  ├─┤├┬┘├┤   └─┐ │ ├┬┘│ ││   │ │ │├┬┘├┤  ││
  ┴ ┴┴─┘┴─┘  └  └─┘┘└┘└─┘ ┴ ┴└─┘┘└┘ └─┘  ┴─┘└─┘└─┘┴  └─┘  ┴ ┴┴└─└─┘  └─┘ ┴ ┴└─└─┘└─┘ ┴ └─┘┴└─└─┘─┴┘

	– Loops must be structured, having an OpLoopMerge instruction in their header.
	– Selections must be structured, having an OpSelectionMerge instruction in their header.
 */




         /* 
			 * This version allows but ignores structurally-unreachable blocks which means that 
			 * structurally control flow rules do not apply to "wholly unreachable" blocks.
			 * For this, we define  StructurallyReachableBlock (as a subset of Block) which contains only
			 * structurally reachable blocks which obey the structurally control flow rules
			 */





open util/relation
//open util/ordering[State] as ord


module StructuredDominanceCFG


sig Block   
{
	branch: seq Block
}


sig  StructurallyReachableBlock  in Block  {} 


let StructurallyUnreachableBlock =  Block -  StructurallyReachableBlock  


/**
  *  "Entry Point: A function in a module where execution begins"
  *  (The Khronos Group, 2021, p.19)
  *  https://www.khronos.org/registry/spir-v/specs/unified1/SPIRV.pdf
  */
one sig EntryBlock in  Block  {}


/**
  *  "Header Block: A block containing a merge instruction"
  *  (The Khronos Group, 2021, p.20)
  *  https://www.khronos.org/registry/spir-v/specs/unified1/SPIRV.pdf
  */
sig HeaderBlock extends  Block    
{
	merge : one  Block 
}


/**
  *  "Loop Header: A header block whose merge instruction is an OpLoopMerge"
  *  (The Khronos Group, 2021, p.20)
  *  https://www.khronos.org/registry/spir-v/specs/unified1/SPIRV.pdf
  */
sig LoopHeader extends HeaderBlock   
{
	continue : one  Block 
}


/**
  *  "Selections must be structured, having an OpSelectionMerge instruction in their header"
  *  (The Khronos Group, 2021, p.37)
  *  https://www.khronos.org/registry/spir-v/specs/unified1/SPIRV.pdf
  *
  */
sig SelectionHeader extends HeaderBlock {}


/**
  *  An OpSwitch block (which contains a multi-way branch instruction) must have, at a minimum,
  *  a successor for the "default" case
  */
sig SwitchBlock in SelectionHeader  {}
{
	some branch
}






/*
       ██████                                  █████     ███
      ███░░███                                ░░███     ░░░
     ░███ ░░░  █████ ████ ████████    ██████  ███████   ████   ██████  ████████    █████
    ███████   ░░███ ░███ ░░███░░███  ███░░███░░░███░   ░░███  ███░░███░░███░░███  ███░░
   ░░░███░     ░███ ░███  ░███ ░███ ░███ ░░░   ░███     ░███ ░███ ░███ ░███ ░███ ░░█████
     ░███      ░███ ░███  ░███ ░███ ░███  ███  ░███ ███ ░███ ░███ ░███ ░███ ░███  ░░░░███
     █████     ░░████████ ████ █████░░██████   ░░█████  █████░░██████  ████ █████ ██████
    ░░░░░       ░░░░░░░░ ░░░░ ░░░░░  ░░░░░░     ░░░░░  ░░░░░  ░░░░░░  ░░░░ ░░░░░ ░░░░░░

 */



/**
  *  'branchSet' maps to the (unordered) set of elements in sequence "branch"
  */
fun branchSet :  Block -> Block 
{
    { A, B: Block | B in ((A.branch).elems) }
}


let stucturalBranch = branchSet + merge + continue


/**
  *  exitBlocks models the set of "Termination Instruction" used to terminate blocks
  *  (The Khronos Group, 2021, p.20)
  *  https://www.khronos.org/registry/spir-v/specs/unified1/SPIRV.pdf
  */
fun exitBlocks :  Block    
{
	{ B:  Block  | no B<:branch}
}


/**
  *  A helper function for the computation of structured-(post)-dominance relation
  */
fun MetaReachableFromWithoutPassingThrough[from,through:  StructurallyReachableBlock ] : set  Block  
{
	from.*(( StructurallyReachableBlock -through) <: stucturalBranch ) - through
}


/**
  *  An augmented notion of dominance:
  *  'A' structurally-dominates 'B' if every path made up of 'branch', 'merge' and 'continue'
  *  edges from the function’s entry point to block 'B' includes block 'A'.

		 Entry
	       ⬇
			  A
		     ⬇
				B
  */
fun structurallyDominates :   Block  ->  Block  
{
	{ A, B:  StructurallyReachableBlock   |  B in A.*stucturalBranch and B not in MetaReachableFromWithoutPassingThrough[EntryBlock,A] }
}


/**
  *  "'A' strictly structurally-dominates 'B' only if 'A' structurally-dominates 'B'
  *   and 'A' and 'B' are different blocks"
  */
fun strictlyStructurallyDominates :  Block  ->  Block 
{
	structurallyDominates - iden
}



/**
  *  An augmented notion of post-dominance:
  *  'B' structurally-post-dominates 'A' if every path made up of 'branch', 'merge' and 'continue'
  *  edges from 'A' to a function-return instruction goes through block 'B'.

		    A
	       ⬇
			  B
		     ⬇
			  Exit
  */
fun structurallyPostDominates :   Block  ->  Block  
{
    { B, A:  Block  | B in A.*stucturalBranch and no exitBlocks & MetaReachableFromWithoutPassingThrough[A,B] }
}


/**
  *  "A back edge is an edge D -> B whose head B structurally-dominates its tail D"
  *
  *   The definition given in the SPIR-V spec..
  *
  *	(The Khronos Group, 2021, p.20)
  *   https://www.khronos.org/registry/spir-v/specs/unified1/SPIRV.pdf
  */
fun backEdgeSeq :  branch 
{
	-- We take into account all parallel back edges (incident to the same pair)
	{ 	 
		D:  Block  , i:Int, B:  Block  |  B->D in structurallyDominates and 	 B in D.branchSet and i >=0 and i < #(D.(branch:>B))
	}
}


/**
  *  'backEdge' maps to the (unordered) set of elements in sequence "backEdgeSeq"
  */
fun backEdge :   Block  ->  Block  
{
    { A, B:  Block  | B in ((A.backEdgeSeq).elems) }
}


/**
  *  "A selection construct: includes the blocks dominated by a selection header,
  *   while excluding blocks dominated by the selection construct’s merge block.
  *
  *   (The Khronos Group, 2021, p.29)
  *   https://www.khronos.org/registry/spir-v/specs/unified1/SPIRV.pdf
  */
fun selectionConstruct [sh: SelectionHeader] :  StructurallyReachableBlock    
{
	(sh&SelectionHeader).structurallyDominates - (sh&SelectionHeader).merge.structurallyDominates
}


/**
  *  "A continue construct: includes the blocks dominated by an OpLoopMerge Continue Target
  *   and post dominated by the corresponding loop’s back-edge block, while excluding blocks
  *   dominated by that loop’s merge block.
  *
  *   (The Khronos Group, 2021, p.29)
  *   https://www.khronos.org/registry/spir-v/specs/unified1/SPIRV.pdf
  *
  *	Defining the continue construct to be the blocks structurally dominated by the continue 
  *	target and structurally post-dominated by the back-edge block should give a 
  *	single-entry-single-exit region of blocks, and surely this cannot include any blocks 
  *	structurally dominated by the loop's merge block, so that we're removing an empty set
  */
fun continueConstruct [ct: LoopHeader.continue] :  StructurallyReachableBlock    
{
	(  ((ct&(LoopHeader.continue)).structurallyDominates) & (((ct&(LoopHeader.continue)).~continue.~backEdge).structurallyPostDominates) ) 
}


/**
  *  "A loop construct: includes the blocks dominated by a loop header, while excluding both
  *   that header’s continue construct and the blocks dominated by the loop’s merge block
  *
  *   (The Khronos Group, 2021, p.29)
  *   https://www.khronos.org/registry/spir-v/specs/unified1/SPIRV.pdf
  */
fun loopConstruct [lh: LoopHeader] :  StructurallyReachableBlock    
{
	(lh&LoopHeader).structurallyDominates - continueConstruct[(lh&LoopHeader).continue] - (lh&LoopHeader).merge.structurallyDominates
}


/**
  *  "A case construct: the blocks dominated by an OpSwitch Target or Default (this construct
  *   is only defined for those OpSwitch Target or Default that are not equal to the OpSwitch’s
  *   corresponding merge block)
  *
  *   (The Khronos Group, 2021, p.29)
  *   https://www.khronos.org/registry/spir-v/specs/unified1/SPIRV.pdf
  *
  *
  *   Changes to definition above:
  *   “a case construct: the blocks structurally dominated by an OpSwitch Target or Default, 
  *    excluding the blocks structurally dominated by the OpSwitch’s corresponding merge block 
  *   (this construct is only defined for those OpSwitch Target or Default that are not equal 
  *    to the OpSwitch’s corresponding merge block)”
  */
fun caseConstruct [t:  StructurallyReachableBlock ] :  StructurallyReachableBlock  
{
  { b:  StructurallyReachableBlock  | let sw = t.~branchSet & SwitchBlock  |
              													    ( some sw	     					    ) 
            												  and  (sw.merge != t 					    ) 
             												  and  (t -> b in structurallyDominates )
																  and  (sw.merge->b not in structurallyDominates)
  }
}


/**
  *  A nested loop is a loop within a loop; an inner loop within the body of an outer one.
  */
fun outerInnerLoop  :  StructurallyReachableBlock  ->  StructurallyReachableBlock  
{
  {
	   disj outH, inH: LoopHeader | inH in loopConstruct[outH]
  }
}


fun outerInner  : Block -> Block {
	{
		disj outer, inner: constructHeader | inner in  selectionConstruct[outer] + 
														 			  loopConstruct[outer]      +
														 			  continueConstruct[outer]  +
																	  caseConstruct[outer]      
	}
}


/**
  *  returns the innermost loop a block (b) is nested inside of
  */
fun innermostLoop[b:   StructurallyReachableBlock ] : lone  StructurallyReachableBlock    
{
	{
		 h: LoopHeader | (  b in loopConstruct[h] ) and (  b not in loopConstruct[h.outerInnerLoop]   )
   }
}


/**
  *  A nested continue construct is one within another;
  */
fun outerInnerContinue  :  StructurallyReachableBlock  ->  StructurallyReachableBlock  
{
  {
	   disj outer, inner: LoopHeader.continue | inner in continueConstruct[outer]
  }
}


/**
  *  returns the innermost continue construct a block (b) is nested inside of
  */
fun innermostContinue[b:   StructurallyReachableBlock ] : lone  StructurallyReachableBlock    
{
	{
		 c: LoopHeader.continue | (  b in continueConstruct[c] ) and (  b not in continueConstruct[c.outerInnerContinue]   )
   }
}


/**
  *  A nested Switch is a switch within a switch; an inner switch within the body of an outer one.
  */
fun outerInnerSW  :  StructurallyReachableBlock  ->  StructurallyReachableBlock  {
	{
		disj outSW, inSW: SwitchBlock | inSW in selectionConstruct[outSW]
	}
}


/**
  *  returns the innermost OpSwitch a block (b) is nested inside of
  */
fun innermostOpSwitch[b:  StructurallyReachableBlock ] : lone  StructurallyReachableBlock    {
	{ 
		sw: SwitchBlock |  ( 	b in selectionConstruct[sw] )	and ( some sw.outerInnerSW => b not in selectionConstruct[sw.outerInnerSW] 	)
	}
}


let constructHeader =  HeaderBlock + LoopHeader.continue + (SwitchBlock.branchSet - SwitchBlock.merge)  


fun contains :  StructurallyReachableBlock  ->  StructurallyReachableBlock  {
	{
	 outer, inner:  StructurallyReachableBlock  

									 | let lCouter = loopConstruct[outer]		, lCinner = loopConstruct[inner], 
											 sCouter = selectionConstruct[outer], sCinner = selectionConstruct[inner] ,
											 ctCouter = continueConstruct[outer], ctCinner = continueConstruct[inner] ,
											 csCouter = caseConstruct[outer] 	, csCinner = caseConstruct[inner],
											 case =  SwitchBlock.branchSet - SwitchBlock.merge
											 
									 |
									
										(outer in LoopHeader and inner in LoopHeader		 	 	and some lCinner  and some lCouter and lCinner  in lCouter ) or
										(outer in LoopHeader and inner in SelectionHeader 		and some sCinner  and some lCouter and sCinner  in lCouter ) or
										(outer in LoopHeader and inner in LoopHeader.continue and some ctCinner and some lCouter and ctCinner in lCouter ) or
										(outer in LoopHeader and inner in case					 	and some csCinner and some lCouter and csCinner in lCouter ) or
								
										(outer in SelectionHeader and inner in LoopHeader		 	  and some lCinner  and some sCouter and lCinner  in sCouter ) or
										(outer in SelectionHeader and inner in SelectionHeader 	  and some sCinner  and some sCouter and sCinner  in sCouter ) or
										(outer in SelectionHeader and inner in LoopHeader.continue and some ctCinner and some sCouter and ctCinner in sCouter ) or
										(outer in SelectionHeader and inner in case					  and some csCinner and some sCouter and csCinner in sCouter ) or

										(outer in LoopHeader.continue and inner in LoopHeader		 	   and some lCinner  and some ctCouter and lCinner  in ctCouter ) or
										(outer in LoopHeader.continue and inner in SelectionHeader 	   and some sCinner  and some ctCouter and sCinner  in ctCouter ) or
										(outer in LoopHeader.continue and inner in LoopHeader.continue and some ctCinner and some ctCouter and ctCinner in ctCouter ) or
										(outer in LoopHeader.continue and inner in case					   and some csCinner and some ctCouter and csCinner in ctCouter ) or

										(outer in SwitchBlock.branchSet and inner in LoopHeader		 	   and some lCinner  and some csCouter and lCinner  in csCouter ) or
										(outer in SwitchBlock.branchSet and inner in SelectionHeader 	   and some sCinner  and some csCouter and sCinner  in csCouter ) or
										(outer in SwitchBlock.branchSet and inner in LoopHeader.continue and some ctCinner and some csCouter and ctCinner in csCouter ) or
										(outer in SwitchBlock.branchSet and inner in case						and some csCinner and some csCouter and csCinner in csCouter ) or

										(outer in LoopHeader 			and inner not in constructHeader	and inner in lCouter )  or
										(outer in SelectionHeader 		and inner not in constructHeader and inner in sCouter )  or 
										(outer in LoopHeader.continue and inner not in constructHeader and inner in ctCouter)  or
										(outer in SwitchBlock.branchSet and inner not in constructHeader and inner in csCouter) 
	}
}


/**
  *	Innermost T construct containing a block: Let T be one of “loop”, “continue”, “selection”.
  *	Let B be a structurally-reachable block in the control flow graph of a function. 
  *	If B is not contained in any T construct, then the innermost T construct containing B is undefined. 
  *	Otherwise, let C be the unique T construct such that:
  *	- C contains B;
  *	- Every T construct that contains B also contains C.
  *	The T construct C is the innermost T construct containing B.
  */
fun innermostConstructHeader[B:  StructurallyReachableBlock ] :  StructurallyReachableBlock    {
	{ 
		C: constructHeader | 	(	B in C.contains) and 
										(
											B not in ((C.contains) & (constructHeader -C)).contains
										 )
	}
}


/**
  *	It could be the case that a block has more than one instance, e.g., loop header and continue target 
  *
  *	let C->D; given a construct header C, if D not in the biggest construct than by computing the smallest construct 
  *	we capture all exits, from smallest and biggest too
  */
fun innermostConstr[B:  StructurallyReachableBlock ] : set  StructurallyReachableBlock    {
	{ 
	  C:  StructurallyReachableBlock  | let inH = innermostConstructHeader[B],		
							lC = loopConstruct[inH]		, 
							sC = selectionConstruct[inH], 
							ctC= continueConstruct[inH], 
							csC= caseConstruct[inH] 																										 
					| 	
						(B in lC => C in lC)   and		
						(B in sC => C in sC)   and		
						(B in ctC => C in ctC) and		
						(B in csC => C in csC) 		
	 	
	}
}


fun exitEdge :  StructurallyReachableBlock  ->  StructurallyReachableBlock  {
    { B, C:  StructurallyReachableBlock  
		 | 
			 let headOfInnermostConst_B = innermostConstructHeader[B], 							   								   						   										
				  innermostConstruct_B 	 = innermostConstr[B]	
		 |	
				C in B.branchSet and some headOfInnermostConst_B and C not in innermostConstruct_B
	} 
}





/*

    ███████████                     █████
   ░░███░░░░░░█                    ░░███
    ░███   █ ░   ██████    ██████  ███████    █████
    ░███████    ░░░░░███  ███░░███░░░███░    ███░░
    ░███░░░█     ███████ ░███ ░░░   ░███    ░░█████
    ░███  ░     ███░░███ ░███  ███  ░███ ███ ░░░░███
    █████      ░░████████░░██████   ░░█████  ██████
   ░░░░░        ░░░░░░░░  ░░░░░░     ░░░░░  ░░░░░░

 */



/**
  *   'StructurallyReachableBlock' is structurally-reachable from Entry
  */
fact 
{
	StructurallyReachableBlock  = EntryBlock.*stucturalBranch
}


/** This fact tells explicitly that merge and continues for a loop must be different.
	 In the spec, this fact is implicit comming from the condition (that otherwise is redundant)
    that "a continue construct must contain its loop's back edge block".


		The spec does not explicitly say that a loop's merge block and continue target 
		have to be different. 

		However, it says: "a continue construct: includes the blocks dominated by an 
		OpLoopMerge Continue Target and post dominated by the corresponding loop’s 
		back-edge block, while excluding blocks dominated by that loop’s merge block"
		
		This implies that if the loop's merge block and continue target were the same block, 
		the loop's continue construct would be empty.

		Because the spec goes on to say: "a continue construct must include its loop’s back-edge block", 
		this implies that a continue construct cannot be empty, which means that a loop's merge block 
		and continue target have to be different.
 */
fact  
{
	all l : LoopHeader & StructurallyReachableBlock | no l.merge & l.continue
}


fact
{
	no EntryBlock.~branchSet
}


fact 
{
	HeaderBlock = LoopHeader + SelectionHeader
}


/** weakly connected (loose ends), i.e., there is a path between every "wholly unreachable" block 
  * b1 and some structurally-reachable block b2 in the underlying undirected graph
  */
pred WeaklyConnected
{
	all b1: StructurallyUnreachableBlock | some b2:  StructurallyReachableBlock  | b1 in b2.*(branchSet + ~branchSet)  
}


/**
  *  "..the merge block declared by a header block must not be a merge block
  *   declared by any other header block"
  *   (The Khronos Group, 2021, p.29)
  *   https://www.khronos.org/registry/spir-v/specs/unified1/SPIRV.pdf
  */
pred UniqueMergeBlock 
{
	all b : HeaderBlock & StructurallyReachableBlock | no b.merge & ((HeaderBlock & StructurallyReachableBlock) - b).merge
}


/**
  *  "..each header-block must strictly dominate its merge-block, unless the merge-block
  *   is unreachable in the CFG"
  *   (The Khronos Group, 2021, p.29)
  *   https://www.khronos.org/registry/spir-v/specs/unified1/SPIRV.pdf
  */
pred HeaderBlockStrictlyStructurallyDominatesItsMergeBlock 
{
	StructurallyReachableBlock <: merge in strictlyStructurallyDominates
}


/**
  *  "..all CFG back edges must branch to a loop header"
  *   (The Khronos Group, 2021, p.20)
  *   https://www.khronos.org/registry/spir-v/specs/unified1/SPIRV.pdf
  */
pred  BackEdgesBranchToLoopHeader 
{
	ran[backEdge] & StructurallyReachableBlock in LoopHeader & StructurallyReachableBlock 
}


/**
  *  "..each loop header has exactly one back edge branching to it"
  *   (The Khronos Group, 2021, p.29)
  *   https://www.khronos.org/registry/spir-v/specs/unified1/SPIRV.pdf
  */
pred OneBackEdgeBranchingToLoopHeader 
{
	all lh :LoopHeader & StructurallyReachableBlock  | one backEdgeSeq :> lh
}


/**
  *  "..the loop header must dominate the Continue Target,
  *   unless the Continue Target is unreachable in the CFG"
  *   (The Khronos Group, 2021, p.29)
  *   https://www.khronos.org/registry/spir-v/specs/unified1/SPIRV.pdf
  */
pred LoopHeaderStructurallyDominatesContinueTarget 
{
	StructurallyReachableBlock <: continue in structurallyDominates
}


/**
  *  "..the Continue Target must dominate the back-edge block"
  *   (The Khronos Group, 2021, p.29)
  *   https://www.khronos.org/registry/spir-v/specs/unified1/SPIRV.pdf
  */
pred ContinueTargetStructurallyDominatesBackEdge 
{
	(~continue.~backEdge) :> StructurallyReachableBlock in structurallyDominates
}


/**
  *  "..the back-edge block must post dominate the Continue Target"
  *   (The Khronos Group, 2021, p.29)
  *   https://www.khronos.org/registry/spir-v/specs/unified1/SPIRV.pdf
  */
pred BackEdgeStructurallyPostDominatesContinueTarget 
{
	StructurallyReachableBlock <: (backEdge.continue) in structurallyPostDominates
}


/**
  *  "...if a construct contains another header block, it also contains that header’s corresponding
		merge block if that merge block is reachable in the CFG"
  *   (The Khronos Group, 2021, p.29)
  *   https://www.khronos.org/registry/spir-v/specs/unified1/SPIRV.pdf
  */
pred ConstructContainsAnotherHeader 
{
	all disj h1,h2: (HeaderBlock & StructurallyReachableBlock) | let lc  = loopConstruct[h1],
												 ctc = continueConstruct[h1.continue],
												 sc  = selectionConstruct[h1],
												 csc = caseConstruct[h1.branchSet - h1.merge]
										 |
										   (h1 in LoopHeader 	  and h2 in lc  => h2.merge in lc )  and
								 			(h1 in LoopHeader 	  and h2 in ctc => h2.merge in ctc)  and
								 			(h1 in SelectionHeader and h2 in sc	 => h2.merge in sc )  and
								 			(h1 in SwitchBlock 	  and h2 in csc => h2.merge in csc)
}


/**
  *  "...a continue construct must include its loop’s back-edge block"
  *   (The Khronos Group, 2021, p.29)
  *   https://www.khronos.org/registry/spir-v/specs/unified1/SPIRV.pdf
  *
  *   This condition is redundant as it is implied by the other rules: see reasoning 
  *	above about the fact that merge and continues for a loop must be different
  */
pred ContinueConstructIncludesItsBackEdge 
{
	all ct: LoopHeader.continue | some ct.~continue.~backEdge & continueConstruct[ct]
}


/**
  *  "...a break block is valid only for the innermost loop it is nested inside of"
  *   (The Khronos Group, 2021, p.29)
  *   https://www.khronos.org/registry/spir-v/specs/unified1/SPIRV.pdf
  */
pred ValidBreakBlock 
{
	all br:  StructurallyReachableBlock  | let  lh = innermostLoop[br] | (some lh and some lh.~outerInnerLoop) => no  (br.branchSet.~merge) & (lh.~outerInnerLoop)
}


/**
  *  "...a continue block is valid only for the innermost loop it is nested inside of"
  *   (The Khronos Group, 2021, p.29)
  *   https://www.khronos.org/registry/spir-v/specs/unified1/SPIRV.pdf
  */
pred ValidContinueBlock 
{
	all cb:  StructurallyReachableBlock   | let lh = innermostLoop[cb] | (some lh and some lh.~outerInnerLoop) => no (cb.branchSet.~continue) & (lh.~outerInnerLoop)
}


/**
  *  "...a branch to an outer OpSwitch merge block is:
  *   valid only for the innermost OpSwitch the branch is nested inside of"
  *   (The Khronos Group, 2021, p.29)
  *   https://www.khronos.org/registry/spir-v/specs/unified1/SPIRV.pdf
  */
pred ValidBranchToOuterOpSwitchMerge 
{
	all  b:  StructurallyReachableBlock , sw: SwitchBlock | let c = innermostOpSwitch[b] | (b in selectionConstruct[sw] and some c and sw != c) 
												=>   sw not in (b.branchSet.~merge & (SwitchBlock - sw)).outerInnerSW
}


/**
  *  "...a branch to an outer OpSwitch merge block is:
  *   not valid if it is nested in a loop that is nested in that OpSwitch"
  *   (The Khronos Group, 2021, p.29)
  *   https://www.khronos.org/registry/spir-v/specs/unified1/SPIRV.pdf
  */
pred InvalidBranchToOuterOpSwitchMerge 
{
	all b:  StructurallyReachableBlock , hInner: LoopHeader, sw: SwitchBlock  |  let l = loopConstruct[hInner] | (b in l and l in caseConstruct[sw.branchSet] )  =>  sw not in ((b.branchSet.~merge & (SwitchBlock -sw)).outerInnerSW)
}


/**
  *  "...a branch from one case construct to another must be for the same OpSwitch"
  *   (The Khronos Group, 2021, p.29)
  *   https://www.khronos.org/registry/spir-v/specs/unified1/SPIRV.pdf
  */
pred NobranchBetweenCaseConstructs 
{
  all sw: (SwitchBlock & StructurallyReachableBlock) | no  (caseConstruct[sw.branchSet] <:branchSet:> caseConstruct[(SwitchBlock - sw).branchSet]  )
}


/**
  *  "...all branches into a construct from reachable blocks outside the construct
  *   must be to the header block"
  *   (The Khronos Group, 2021, p.29)
  *   https://www.khronos.org/registry/spir-v/specs/unified1/SPIRV.pdf
  */
pred BranchesBetweenConstructs 
{
	all  lh: LoopHeader & StructurallyReachableBlock     		   									      | let lc  = loopConstruct[lh], ctc = continueConstruct[lh.continue]	| (some lc  => no ( StructurallyReachableBlock  - lc)  <: branchSet :> (lc - lh)) and  (some ctc => no ( StructurallyReachableBlock  - ctc) <: branchSet :> (ctc - lh.continue ))   
	all  sh: SelectionHeader & StructurallyReachableBlock 										         | let sc  = selectionConstruct[sh]  | some sc  => no ( StructurallyReachableBlock  - sc)  <: branchSet :> (sc - sh)
	all  sw_target : ((SwitchBlock.branchSet - SwitchBlock.merge) & StructurallyReachableBlock)  | let csc = caseConstruct[sw_target]| some csc => no ( StructurallyReachableBlock  - csc) <: branchSet :> (csc - sw_target)
}


/**
  *  "...an OpSwitch block dominates all its defined case constructs"
  *   (The Khronos Group, 2021, p.29)
  *   https://www.khronos.org/registry/spir-v/specs/unified1/SPIRV.pdf
  */
pred OpSwitchBlockDominatesAllItsCases 
{
	all sw: (SwitchBlock & StructurallyReachableBlock)  | (sw <:branchSet:> ( StructurallyReachableBlock  - sw.merge)) in structurallyDominates
}


/**
  *  "...each case construct has at most one branch to another case construct"
  *   (The Khronos Group, 2021, p.29)
  *   https://www.khronos.org/registry/spir-v/specs/unified1/SPIRV.pdf
*/
pred AtMostOneBranchToAnotherCaseConstruct 
{
	all sw: (SwitchBlock & StructurallyReachableBlock), from: sw.branchSet - sw.merge | let case_construct_from = caseConstruct[from] |																				
															lone case_construct_from  <:branchSet:> (selectionConstruct[sw] - sw - case_construct_from)
}


/**
  *  "...each case construct is branched to by at most one other case construct"
  *   (The Khronos Group, 2021, p.29)
  *   https://www.khronos.org/registry/spir-v/specs/unified1/SPIRV.pdf
  */
pred CaseConstructBranchedToByAtMostOneOther 
{
	all sw: (SwitchBlock & StructurallyReachableBlock), to: sw.branchSet - sw.merge | let case_construct_to = caseConstruct[to] |																				
															lone (selectionConstruct[sw] - sw - case_construct_to) <:branchSet:> case_construct_to
}


/**
  *  "...if Target T1 branches to Target T2, or if Target T1 branches to the Default
  *  and the Default branches to Target T2, then T1 must immediately precede T2
  *  in the list of the OpSwitch Target operands"
  *  (The Khronos Group, 2021, p.29)
  *  https://www.khronos.org/registry/spir-v/specs/unified1/SPIRV.pdf
  *
  *
  *  The above rule is adjusted as follows:
  *
  *  (a) if 'T1' and 'T2' appear as labels of targets in the **OpSwitch**
  *      instruction and the case construct defined by 'T1' branches to
  *      the case construct defined by 'T2' then the last target with label 'T1' 
  *      must immediately precede the first target with label 'T2' in the list of 
  *      *OpSwitch* 'Target' operands
  *
  *  (b) if 'T1' and 'T2' appear as labels of targets in the **OpSwitch**
  *      instruction and the case construct defined by 'T1' branches to the
  *      'Default' case construct of the **OpSwitch** which in turn
  *      branches to the case construct defined by 'T2', then either:
  *
  *      (i)   the block that defines the 'Default' case construct must
  *            appear as a target label in the **OpSwitch** instruction, or
  *      (ii)  the last target with label 'T1' must immediately precede the
  *            first target with label 'T2' in the list of **OpSwitch**
  *           'Target' operands
  *
  *  (c) for any label 'T', all targets with label 'T' must appear consecutively 
  *      in the list of *OpSwitch* 'Target' operands
  *
  */
pred OrderOfOpSwitchTargetOperands 
{
	-- branch[0] is the default block
	all sw: (SwitchBlock & StructurallyReachableBlock), 
		 disj T1,T2: sw.branch.rest.elems, 
		 t1: caseConstruct[T1], 
		 t2: caseConstruct[T2] 		|  let default = sw.branch.first, tail = sw.branch.rest |
 
												(
													some t1 and some t2 and
													(
														( some t1 <:branchSet:> T2 ) ||
																							   (
																									(some t1 <:branchSet:> default) and 
																									 no  ((tail.elems)&default)     and
																									(some caseConstruct[default]<:branchSet:>T2)
																								)
														)
													)
																
													=>   ( idxOf [tail, T2] = lastIdxOf [tail, T1].add[1] )
														
	all sw: (SwitchBlock & StructurallyReachableBlock), T: sw.branch.rest.elems | let tail = sw.branch.rest |
  													(tail.subseq [idxOf [tail, T], lastIdxOf [tail, T]]).elems = T // this checks whether the substring of occurrences of T is consecutive
}


/**
  *  "The first block in a function definition is the entry point of that
  *   function and must not be the target of any branch."
  *   (The Khronos Group, 2021, p.35)
  *   https://www.khronos.org/registry/spir-v/specs/unified1/SPIRV.pdf
  *
  *   This also implies that the entry point is not a LoopHeader because 
  *   otherwise it would be targeted by the back-edge
  */
pred EntryBlockIsNotTargeted
{
	EntryBlock not in ran[branchSet]
}


/**
  *  "OpLoopMerge must immediately precede either an OpBranch or OpBranchConditional
  *   instruction. That is, it must be the second-to-last instruction in its block."
  *   (The Khronos Group, 2021, p.210)
  *   https://www.khronos.org/registry/spir-v/specs/unified1/SPIRV.pdf
  */
pred OpLoopMergeSecondToLast 
{
	{ all l: (LoopHeader & StructurallyReachableBlock) | (one l<:branch ) or (#(l<:branch) = 2) }
}


/**
  *   "OpSelectionMerge must immediately precede either an OpBranchConditional or
  * .  OpSwitch instruction. That is, it must be the second-to-last instruction in its block."
  *   (The Khronos Group, 2021, p.211)
  *   https://www.khronos.org/registry/spir-v/specs/unified1/SPIRV.pdf
  */
pred OpSelectionMergeSecondToLast 
{
	{ all s: ((SelectionHeader - SwitchBlock) & StructurallyReachableBlock) | #(s<:branch) = 2  }
}


/**
  *   "OpSwitch: Multi-way branch to one of the operand label <id>."
  *   (The Khronos Group, 2021, p.212)
  *   https://www.khronos.org/registry/spir-v/specs/unified1/SPIRV.pdf
  *
  *   Unconditional branchs have at most two successors
  *
  */
pred OutDegree 
{
	{all b: StructurallyReachableBlock  | b in SwitchBlock => some b<:branch else #(b<:branch) <= 2}
}


/**
  *   Restrict when multiple outgoing edges are allowed
  *
  *   A non-header block B can have 2 successors, C and D, if at least one of the edges B->C and B->D is an exit edge.
  *
  *   For header blocks we have already established the outdegrees
  */
pred MultipleOutEdges 
{
	all b: StructurallyReachableBlock - HeaderBlock | (#(b.branchSet) >1)  => some b<:exitEdge												 										     
}


pred ExitingTheConstruct
{
	{all disj a,b:  StructurallyReachableBlock 
								 | let headOfInnermostConst_a = innermostConstructHeader[a], 							   								   						   										
								   	 innermostConstruct_a 	= innermostConstr[a] 		,					   								   						   										
								   	 headOfInnermostConst_b = innermostConstructHeader[b], 	
										 headOfInnermostLoop_a  = innermostLoop[a],
										 innermostLoopConst_a 	= loopConstruct[headOfInnermostLoop_a],
										 headOfInnermostSW_a    = innermostOpSwitch[a], 																									 
										 headOfinnermostContinueConst_a = innermostContinue[a],
										 innermostContinueConst_a 	= 	continueConstruct[headOfinnermostContinueConst_a]	 		  								
						       | 

							    	 (
										 b in a.branchSet 					and 
										 some headOfInnermostConst_a		and   --i.e., a is nested at some construct
										 b not in innermostConstruct_a 	and   --i.e., b is outside the innermost of a
										 (
											 some ((headOfInnermostConst_a.~branchSet & headOfInnermostConst_b.~branchSet) & SwitchBlock) //case->case												 
														=>	a in innermostConstr[headOfInnermostConst_a & (HeaderBlock + LoopHeader.continue)]  
										 )
									  )

									   => 

							   			(
												-- Normal exit from a construct: 
		    									(some a <:branchSet:> (headOfInnermostConst_a.merge & b )  )   or

												-- ...for a continue construct, a normal exit implies that 'a' is the back-edge block for the loop associated with the continue construct
		    									 (headOfInnermostConst_a 	 in LoopHeader.continue	and some (a & headOfInnermostConst_a.~continue.~backEdge) <:branchSet:> (headOfInnermostConst_a.~continue.merge & b) )   or

												-- Branching from a back-edge block to a loop header:
												 (headOfInnermostConst_a in LoopHeader.continue	and some (a & headOfinnermostContinueConst_a.~continue.~backEdge) <:branchSet:> (headOfinnermostContinueConst_a.~continue & b))	or

												-- Branching to a loop merge from a non back-edge block: 
												 ( (no a & LoopHeader.~backEdge) and (some headOfInnermostLoop_a & LoopHeader)	and (some innermostContinueConst_a => headOfInnermostLoop_a in innermostContinueConst_a) and  (some a <:branchSet:> (headOfInnermostLoop_a.merge & b) )  )	or

												-- Branching to a loop continue target from a non back-edge block: 
												 ( (no a & LoopHeader.~backEdge) and (some headOfInnermostLoop_a & LoopHeader)	and (some innermostContinueConst_a => headOfInnermostLoop_a in innermostContinueConst_a) and  (some a <:branchSet:> (headOfInnermostLoop_a.continue & b) )  ) or

												-- Branching to a switch merge: 	
												 (some headOfInnermostSW_a and (some innermostContinueConst_a => headOfInnermostSW_a in innermostContinueConst_a) and (some innermostLoopConst_a => headOfInnermostSW_a in innermostLoopConst_a)	and  some a <:branchSet:> (headOfInnermostSW_a.merge & b))   
		  							   	)							 
	}
}


pred StructurallyAcyclic 
{
	no ^(StructurallyReachableBlock <: (stucturalBranch - backEdge)) & iden -- the result is structurally acyclic after removing self-loops and back edges
}


/**
  *  Let B be a continue target; suppose that B is not a loop header and let A->B a control flow edge.
  *  Then A is part of the loop associated with B. The rule also excludes consideration of backedges.
  *
  *  [The old version of spirv-val accepts edges like the ones in the following GitHub issue:
  *   https://github.com/afd/spirv-control-flow/issues/28]
  */
pred BranchToContinue 
{
	all l: (LoopHeader & StructurallyReachableBlock) | l != l.continue => no (StructurallyReachableBlock - loopConstruct[l]) <: (branchSet - backEdge) :> l.continue 
}


/**
  * If B is a loop header and B has two successors then 
  * at least one of the successors must be the loop merge block or 
  * the loop continue target
  */
pred AvoidConditionalBrancOnLoopHeaderThatDoesNotTargetAMergeOrContinue 
{
	all l: (LoopHeader & StructurallyReachableBlock) | #(l<:branch) = 2 => some l.((continue + merge)& branchSet) 
}


pred	 ex {}


pred Valid { 

	UniqueMergeBlock 
	HeaderBlockStrictlyStructurallyDominatesItsMergeBlock 
	BackEdgesBranchToLoopHeader 
	OneBackEdgeBranchingToLoopHeader 
	LoopHeaderStructurallyDominatesContinueTarget 
	ContinueTargetStructurallyDominatesBackEdge 
	BackEdgeStructurallyPostDominatesContinueTarget 
	ConstructContainsAnotherHeader 
	ValidBreakBlock 
	ValidContinueBlock 
	ValidBranchToOuterOpSwitchMerge 
	InvalidBranchToOuterOpSwitchMerge 
	NobranchBetweenCaseConstructs 
	BranchesBetweenConstructs 
	OpSwitchBlockDominatesAllItsCases 
	AtMostOneBranchToAnotherCaseConstruct 
	CaseConstructBranchedToByAtMostOneOther 
	OrderOfOpSwitchTargetOperands
	EntryBlockIsNotTargeted 
	OpLoopMergeSecondToLast 
	OpSelectionMergeSecondToLast
	OutDegree 
	MultipleOutEdges 
   ExitingTheConstruct 
	StructurallyAcyclic
   BranchToContinue
	AvoidConditionalBrancOnLoopHeaderThatDoesNotTargetAMergeOrContinue
}




pred loop_example {
/*
 * This control flow graph is invalid according to the SPIR-V Specification Version 1.5 wording 
 * because the loop headed by b2 has no back edge: edge b4->b2 is not a back edge since b4 is unreachable.
 * In structural semantics, however, this example is deemed valid.
 */
  some disj b1, b2, b3, b4 :  StructurallyReachableBlock  {
    EntryBlock  = b1
    HeaderBlock = b2
    LoopHeader  = b2
    SwitchBlock = none
    branch   = (b1 -> (0 -> b2))
             + (b2 -> (0 -> b3))
             + (b4 -> (0 -> b2))
    merge    = (b2 -> b3)
    continue = (b2 -> b4)
  }
}
--test1: run { loop_example && Valid  } for 4 Block


pred invalid_example {
/* 
 * Here the rule: "ConstructContainsAnotherHeader: ..if a construct contains the header block of another construct, 
 * it should also contain that construct's merge block" is violated because b3 (which is a header) 
 * is contained in the continue construct but b4 (the merge of b3) is not.
 */
  some disj b1, b2, b3, b4, b5 :  StructurallyReachableBlock  {
    EntryBlock  = b1
    HeaderBlock = b2 + b3
    LoopHeader  = b2
    SwitchBlock = none
    branch   = (b1 -> (0 -> b2))
             + (b2 -> (0 -> b3))
             + (b3 -> ((0 -> b2) + (1 -> b5)))
             + (b4 -> (0 -> b5))
    merge    = (b2 -> b5)
             + (b3 -> b4)
    continue = (b2 -> b3)
  }
}
--test2: run { invalid_example && Valid } for 5 Block

pred Vibrant 
/*
 * There should not exist Blocks A, B, C, such that:
 * B is the only structural-successor of A
 * A is the only structural-predecessor of B
 * C is the only structural-successor of B
 * B is the only structural-predecessor of C
 */
{
	all disj A,B,C: Block | not (   B = A. stucturalBranch - A and
											  A = B.~stucturalBranch - B and
											  C = B. stucturalBranch - B and
											  B = C.~stucturalBranch - C
										  )
										 
	all sw: SwitchBlock | #(sw<:branch) <= 3

	all  a,b: Block | #(a<:branch:>b) < 2
}

pred MoreInteresting
{
	/* no 2 outmost constructs - we impose here a more nested setup
	 * we also impose existence of at least one loop as Alloy is lazily avoiding them
	 */
	all disj h1,h2: HeaderBlock | some (h1+h2).~outerInner
	#LoopHeader > 0
	all l: LoopHeader | l not in l.continue.branchSet
}

-- these four commands will generate valid instances of the model
run {  Valid && Vibrant && MoreInteresting  && Block = StructurallyReachableBlock } for exactly 8 Block 
run {  Valid && Vibrant && MoreInteresting  && Block = StructurallyReachableBlock } for exactly 10 Block 
run {  Valid && Vibrant && MoreInteresting  && Block = StructurallyReachableBlock } for exactly 12 Block 
run {  Valid && Vibrant && MoreInteresting  && Block = StructurallyReachableBlock } for exactly 14 Block 

-- the following command will generate invalid instances of the model that violate one of the constraint
run { UniqueMergeBlock && HeaderBlockStrictlyStructurallyDominatesItsMergeBlock && not BackEdgesBranchToLoopHeader && OneBackEdgeBranchingToLoopHeader && LoopHeaderStructurallyDominatesContinueTarget && ContinueTargetStructurallyDominatesBackEdge && BackEdgeStructurallyPostDominatesContinueTarget && not ConstructContainsAnotherHeader && ValidBreakBlock && ValidContinueBlock && ValidBranchToOuterOpSwitchMerge && InvalidBranchToOuterOpSwitchMerge && NobranchBetweenCaseConstructs && BranchesBetweenConstructs && OpSwitchBlockDominatesAllItsCases && AtMostOneBranchToAnotherCaseConstruct && CaseConstructBranchedToByAtMostOneOther && OrderOfOpSwitchTargetOperands && EntryBlockIsNotTargeted && OpLoopMergeSecondToLast && OpSelectionMergeSecondToLast && OutDegree && MultipleOutEdges && ExitingTheConstruct && StructurallyAcyclic && BranchToContinue &&  Vibrant && MoreInteresting && Block = StructurallyReachableBlock  } for exactly 8 Block

