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
			 * This version allows but ignores structurally-unreachable Blocks which means that 
			 * structurally control flow rules do not apply to "wholly unreachable" Blocks.
			 * For this, we define Block (as a sub-type of BLOCK) which contains only
			 * structurally reachable Blocks which obey the structurally control flow rules
			 */





open util/relation
//open util/ordering[State] as ord


module StructuredDominanceCFG


sig BLOCK   
{
	jump: seq BLOCK
}


sig Block extends BLOCK  {} // structurally reachable Blocks


let Unreachable =  BLOCK - Block 


/**
  *  "Entry Point: A function in a module where execution begins"
  *  (The Khronos Group, 2021, p.19)
  *  https://www.khronos.org/registry/spir-v/specs/unified1/SPIRV.pdf
  */
one sig EntryPoint in Block {}


/**
  *  "Header Block: A Block containing a merge instruction"
  *  (The Khronos Group, 2021, p.20)
  *  https://www.khronos.org/registry/spir-v/specs/unified1/SPIRV.pdf
  */
sig HeaderBlock extends Block   
{
	merge : one Block
}


/**
  *  "Loop Header: A header Block whose merge instruction is an OpLoopMerge"
  *  (The Khronos Group, 2021, p.20)
  *  https://www.khronos.org/registry/spir-v/specs/unified1/SPIRV.pdf
  */
sig LoopHeader extends HeaderBlock   
{
	continue : one Block
}


/**
  *  "Selections must be structured, having an OpSelectionMerge instruction in their header"
  *  (The Khronos Group, 2021, p.37)
  *  https://www.khronos.org/registry/spir-v/specs/unified1/SPIRV.pdf
  *
  */
sig SelectionHeader extends HeaderBlock {}


/**
  *  An OpSwitch Block (which contains a multi-way branch instruction) must have, at a minimum,
  *  a successor for the "default" case
  */
sig SwitchBlock in SelectionHeader  {}
{
	some jump
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
  *  'jumpSet' maps to the (unordered) set of elements in sequence "jump"
  */
fun jumpSet :  BLOCK -> BLOCK 
{
    { A, B: BLOCK | B in ((A.jump).elems) }
}


fun structurallyReachable :  set Block 
{
     EntryPoint.*(jumpSet + merge + continue)
}


/**
  *  exitNodes models the set of "Termination Instruction" used to terminate Blocks
  *  (The Khronos Group, 2021, p.20)
  *  https://www.khronos.org/registry/spir-v/specs/unified1/SPIRV.pdf
  */
fun exitNodes : Block   
{
	{ B: Block | no B<:jump}
	--EntryPoint + ran[jumpSet] - dom[jumpSet]
}


/**
  *  A helper function for the computation of structured-(post)-dominance relation
  */
fun MetaReachableFromWithoutPassingThrough[from,through: Block] : set Block 
{
	from.*((Block-through) <: (jumpSet + merge + continue) ) - through
}


/**
  *  An augmented notion of dominance:
  *  'A' structurally-dominates 'B' if every path made up of 'jump', 'merge' and 'continue'
  *  edges from the function’s entry point to Block 'B' includes Block 'A'.

		 Entry
	       ⬇
			  A
		     ⬇
				B
  */
fun structurallyDominates :  Block -> Block 
{
	{ A, B: Block  |  B in A.*(jumpSet + merge + continue) and B not in MetaReachableFromWithoutPassingThrough[EntryPoint,A] }
}


/**
  *  "'A' strictly structurally-dominates 'B' only if 'A' structurally-dominates 'B'
  *   and 'A' and 'B' are different Blocks"
  */
fun strictlyStructurallyDominates : Block -> Block
{
	structurallyDominates - iden
}



/**
  *  An augmented notion of post-dominance:
  *  'B' structurally-post-dominates 'A' if every path made up of 'jump', 'merge' and 'continue'
  *  edges from 'A' to a function-return instruction goes through Block 'B'.

		    A
	       ⬇
			  B
		     ⬇
			  Exit
  */
fun structurallyPostDominates :  Block -> Block 
{
    { B, A: Block | B in A.*(jumpSet + merge + continue) and no exitNodes & MetaReachableFromWithoutPassingThrough[A,B] }
}


/**
  *  "A back edge is an edge D -> B whose head B structurally-dominates its tail D"
  *
  *   The definition given in the SPIR-V spec..
  *
  *	(The Khronos Group, 2021, p.20)
  *   https://www.khronos.org/registry/spir-v/specs/unified1/SPIRV.pdf
  */
fun backEdgeSeq :  jump 
{
	-- [We take care that all parallel back edges (incident to the same pair) are counted]
	{ 	 
		D: Block , i:Int, B: Block |  B->D in structurallyDominates and 	 B in D.jumpSet and i >=0 and i < #(D.(jump:>B))
	}
}


/**
  *  'backEdge' maps to the (unordered) set of elements in sequence "backEdgeSeq"
  */
fun backEdge :  Block -> Block 
{
    { A, B: Block | B in ((A.backEdgeSeq).elems) }
}


/**
  *  "A selection construct: includes the Blocks dominated by a selection header,
  *   while excluding Blocks dominated by the selection construct’s merge Block.
  *
  *   (The Khronos Group, 2021, p.29)
  *   https://www.khronos.org/registry/spir-v/specs/unified1/SPIRV.pdf
  */
fun selectionConstruct [sh: SelectionHeader] : Block   
{
	(sh&SelectionHeader).structurallyDominates - (sh&SelectionHeader).merge.structurallyDominates
}


/**
  *  "A continue construct: includes the Blocks dominated by an OpLoopMerge Continue Target
  *   and post dominated by the corresponding loop’s back-edge Block, while excluding Blocks
  *   dominated by that loop’s merge Block.
  *
  *   (The Khronos Group, 2021, p.29)
  *   https://www.khronos.org/registry/spir-v/specs/unified1/SPIRV.pdf
  *
  *	Defining the continue construct to be the blocks structurally dominated by the continue 
  *	target and structurally post-dominated by the back-edge block should give a 
  *	single-entry-single-exit region of blocks, and surely this cannot include any blocks 
  *	structurally dominated by the loop's merge block, so that we're removing an empty set
  */
fun continueConstruct [ct: LoopHeader.continue] : Block   
{
	(  ((ct&(LoopHeader.continue)).structurallyDominates) & (((ct&(LoopHeader.continue)).~continue.~backEdge).structurallyPostDominates) ) 
}


/**
  *  "A loop construct: includes the Blocks dominated by a loop header, while excluding both
  *   that header’s continue construct and the Blocks dominated by the loop’s merge Block
  *
  *   (The Khronos Group, 2021, p.29)
  *   https://www.khronos.org/registry/spir-v/specs/unified1/SPIRV.pdf
  */
fun loopConstruct [lh: LoopHeader] : Block   
{
	(lh&LoopHeader).structurallyDominates - continueConstruct[(lh&LoopHeader).continue] - (lh&LoopHeader).merge.structurallyDominates
}


/**
  *  "A case construct: the Blocks dominated by an OpSwitch Target or Default (this construct
  *   is only defined for those OpSwitch Target or Default that are not equal to the OpSwitch’s
  *   corresponding merge Block)
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
fun caseConstruct [t: Block] : Block 
{
  { b: Block | let sw = t.~jumpSet & SwitchBlock  |
              													    ( some sw	     					    ) 
            												  and  (sw.merge != t 					    ) 
             												  and  (t -> b in structurallyDominates )
																  and  (sw.merge->b not in structurallyDominates)
  }
}


/**
  *  A nested loop is a loop within a loop; an inner loop within the body of an outer one.
  */
fun outerInnerLoop  : Block -> Block 
{
  {
	   disj outH, inH: LoopHeader | inH in loopConstruct[outH]
  }
}


/**
  *  returns the innermost loop a Block (b) is nested inside of
  */
fun innermostLoop[b:  Block] : lone Block   
{
	{
		 h: LoopHeader | (  b in loopConstruct[h] ) and (  b not in loopConstruct[h.outerInnerLoop]   )
   }
}


/**
  *  A nested continue construct is one within another;
  */
fun outerInnerContinue  : Block -> Block 
{
  {
	   disj outer, inner: LoopHeader.continue | inner in continueConstruct[outer]
  }
}


/**
  *  returns the innermost continue construct a Block (b) is nested inside of
  */
fun innermostContinue[b:  Block] : lone Block   
{
	{
		 c: LoopHeader.continue | (  b in continueConstruct[c] ) and (  b not in continueConstruct[c.outerInnerContinue]   )
   }
}


/**
  *  A nested Switch is a switch within a switch; an inner switch within the body of an outer one.
  */
fun outerInnerSW  : Block -> Block {
	{
		disj outSW, inSW: SwitchBlock | inSW in selectionConstruct[outSW]
	}
}


/**
  *  returns the innermost OpSwitch a Block (b) is nested inside of
  */
fun innermostOpSwitch[b: Block] : lone Block   {
	{ 
		sw: SwitchBlock |  ( 	b in selectionConstruct[sw] )	and ( some sw.outerInnerSW => b not in selectionConstruct[sw.outerInnerSW] 	)
	}
}


let constructHeader =  HeaderBlock + LoopHeader.continue + (SwitchBlock.jumpSet - SwitchBlock.merge)  


fun contains : Block -> Block {
	{
	 outer, inner: Block 

									 | let lCouter = loopConstruct[outer]		, lCinner = loopConstruct[inner], 
											 sCouter = selectionConstruct[outer], sCinner = selectionConstruct[inner] ,
											 ctCouter = continueConstruct[outer], ctCinner = continueConstruct[inner] ,
											 csCouter = caseConstruct[outer] 	, csCinner = caseConstruct[inner],
											 case =  SwitchBlock.jumpSet - SwitchBlock.merge
											 
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

										(outer in SwitchBlock.jumpSet and inner in LoopHeader		 	   and some lCinner  and some csCouter and lCinner  in csCouter ) or
										(outer in SwitchBlock.jumpSet and inner in SelectionHeader 	   and some sCinner  and some csCouter and sCinner  in csCouter ) or
										(outer in SwitchBlock.jumpSet and inner in LoopHeader.continue and some ctCinner and some csCouter and ctCinner in csCouter ) or
										(outer in SwitchBlock.jumpSet and inner in case						and some csCinner and some csCouter and csCinner in csCouter ) or

										(outer in LoopHeader 			and inner not in constructHeader	and inner in lCouter )  or
										(outer in SelectionHeader 		and inner not in constructHeader and inner in sCouter )  or 
										(outer in LoopHeader.continue and inner not in constructHeader and inner in ctCouter)  or
										(outer in SwitchBlock.jumpSet and inner not in constructHeader and inner in csCouter) 
	}
}


/**
  *	Innermost T construct containing a Block: Let T be one of “loop”, “continue”, “selection”.
  *	Let B be a structurally-reachable Block in the control flow graph of a function. 
  *	If B is not contained in any T construct, then the innermost T construct containing B is undefined. 
  *	Otherwise, let C be the unique T construct such that:
  *	- C contains B;
  *	- Every T construct that contains B also contains C.
  *	The T construct C is the innermost T construct containing B.
  */
fun innermostConstructHeader[B: Block] : Block   {
	{ 
		C: constructHeader | 	(	B in C.contains) and 
										(
											B not in ((C.contains) & (constructHeader -C)).contains
										 )
	}
}


/**
  *	It could be the case that a Block has more than one instance, e.g., loop header and continue target 
  *
  *	let C->D; given a construct header C, if D not in the biggest construct than by computing the smallest construct 
  *	we capture all exits, from smallest and biggest too
  */
fun innermostConstr[B: Block] : set Block   {
	{ 
	  C: Block | let inH = innermostConstructHeader[B],		
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


fun exitEdge : Block -> Block {
    { B, C: Block 
		 | 
			 let headOfInnermostConst_B = innermostConstructHeader[B], 							   								   						   										
				  innermostConstruct_B 	 = innermostConstr[B]	
		 |	
				C in B.jumpSet and some headOfInnermostConst_B and C not in innermostConstruct_B
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


fact  
{
	all l : LoopHeader | no l.merge & l.continue
}


fact
{
	no EntryPoint.~jumpSet
}


fact 
{
	HeaderBlock = LoopHeader + SelectionHeader
}


/**
  *  Block is structurally-reachable from Entry
  */
pred BlockStructurallyReachableFromRoot
{
	Block in structurallyReachable
	no Unreachable & structurallyReachable

	/* weakly connected (loose ends), i.e., there is a path between every "wholly unreachable" block 
	 * b1 \in Unreachable and some structurally-reachable block b2 \in Block 
	 * in the underlying undirected graph
	 */
	all b1: Unreachable | some b2: Block | b1 in b2.*(jumpSet + ~jumpSet)  
}


/**
  *  "..the merge Block declared by a header Block must not be a merge Block
  *   declared by any other header Block"
  *   (The Khronos Group, 2021, p.29)
  *   https://www.khronos.org/registry/spir-v/specs/unified1/SPIRV.pdf
  */
pred UniqueMergeBlock 
{
	all b : HeaderBlock | no b.merge & (HeaderBlock - b).merge
}


/**
  *  "..each header Block must strictly dominate its merge Block, unless the merge Block
  *   is unreachable in the CFG"
  *   (The Khronos Group, 2021, p.29)
  *   https://www.khronos.org/registry/spir-v/specs/unified1/SPIRV.pdf
  */
pred HeaderBlockStrictlyDominatesItsMergeBlock 
{
	-- All Blocks in our model are structurally reachable hence the neglect for "unreachable" merge Blocks
	merge in strictlyStructurallyDominates
}


/**
  *  "..all CFG back edges must branch to a loop header"
  *   (The Khronos Group, 2021, p.20)
  *   https://www.khronos.org/registry/spir-v/specs/unified1/SPIRV.pdf
  */
pred  BackEdgesBranchToLoopHeader 
{
	ran[backEdge] in LoopHeader
}


/**
  *  "..each loop header has exactly one back edge branching to it"
  *   (The Khronos Group, 2021, p.29)
  *   https://www.khronos.org/registry/spir-v/specs/unified1/SPIRV.pdf
  */
pred OneBackEdgeBranchingToLoopHeader 
{
	all lh :LoopHeader | one backEdgeSeq :> lh
}


/**
  *  "..the loop header must dominate the Continue Target,
  *   unless the Continue Target is unreachable in the CFG"
  *   (The Khronos Group, 2021, p.29)
  *   https://www.khronos.org/registry/spir-v/specs/unified1/SPIRV.pdf
  */
pred LoopHeaderDominatesContinueTarget 
{
	-- All Blocks in our model are structurally reachable hence the neglect for "unreachable" merge Blocks
	continue in structurallyDominates
}


/**
  *  "..the Continue Target must dominate the back-edge Block"
  *   (The Khronos Group, 2021, p.29)
  *   https://www.khronos.org/registry/spir-v/specs/unified1/SPIRV.pdf
  */
pred ContinueTargetDominatesBackEdge 
{
	~continue.~backEdge in structurallyDominates
}


/**
  *  "..the back-edge Block must post dominate the Continue Target"
  *   (The Khronos Group, 2021, p.29)
  *   https://www.khronos.org/registry/spir-v/specs/unified1/SPIRV.pdf
  */
pred BackEdgePostDominatesContinueTarget 
{
	backEdge.continue in structurallyPostDominates
}


/**
  *  "...if a construct contains another header Block, it also contains that header’s corresponding
		merge Block if that merge Block is reachable in the CFG"
  *   (The Khronos Group, 2021, p.29)
  *   https://www.khronos.org/registry/spir-v/specs/unified1/SPIRV.pdf
  */
pred ConstructContainsAnotherHeader 
{
	all disj h1,h2: HeaderBlock | let lc  = loopConstruct[h1],
												 ctc = continueConstruct[h1.continue],
												 sc  = selectionConstruct[h1],
												 csc = caseConstruct[h1.jumpSet - h1.merge]
										 |
										   (h1 in LoopHeader 	  and h2 in lc  => h2.merge in lc )  and
								 			(h1 in LoopHeader 	  and h2 in ctc => h2.merge in ctc)  and
								 			(h1 in SelectionHeader and h2 in sc	 => h2.merge in sc )  and
								 			(h1 in SwitchBlock 	  and h2 in csc => h2.merge in csc)
}


/**
  *  "...a continue construct must include its loop’s back-edge Block"
  *   (The Khronos Group, 2021, p.29)
  *   https://www.khronos.org/registry/spir-v/specs/unified1/SPIRV.pdf
  */
pred ContinueConstructIncludesItsBackEdge 
{
	all ct: LoopHeader.continue | some ct.~continue.~backEdge & continueConstruct[ct]
}


/**
  *  "...a break Block is valid only for the innermost loop it is nested inside of"
  *   (The Khronos Group, 2021, p.29)
  *   https://www.khronos.org/registry/spir-v/specs/unified1/SPIRV.pdf
  */
pred ValidBreakBlock 
{
	all br: Block | let  lh = innermostLoop[br] | (some lh and some lh.~outerInnerLoop) => no  (br.jumpSet.~merge) & (lh.~outerInnerLoop)
}


/**
  *  "...a continue Block is valid only for the innermost loop it is nested inside of"
  *   (The Khronos Group, 2021, p.29)
  *   https://www.khronos.org/registry/spir-v/specs/unified1/SPIRV.pdf
  */
pred ValidContinueBlock 
{
	all cb: Block  | let lh = innermostLoop[cb] | (some lh and some lh.~outerInnerLoop) => no (cb.jumpSet.~continue) & (lh.~outerInnerLoop)
}


/**
  *  "...a branch to an outer OpSwitch merge Block is:
  *   valid only for the innermost OpSwitch the branch is nested inside of"
  *   (The Khronos Group, 2021, p.29)
  *   https://www.khronos.org/registry/spir-v/specs/unified1/SPIRV.pdf
  */
pred ValidBranchToOuterOpSwitchMerge 
{
	all  b: Block, sw: SwitchBlock | let c = innermostOpSwitch[b] | (b in selectionConstruct[sw] and some c and sw != c) 
												=>   sw not in (b.jumpSet.~merge & (SwitchBlock - sw)).outerInnerSW
}


/**
  *  "...a branch to an outer OpSwitch merge Block is:
  *   not valid if it is nested in a loop that is nested in that OpSwitch"
  *   (The Khronos Group, 2021, p.29)
  *   https://www.khronos.org/registry/spir-v/specs/unified1/SPIRV.pdf
  */
pred InvalidBranchToOuterOpSwitchMerge 
{
	all b: Block, hInner: LoopHeader, sw: SwitchBlock  |  let l = loopConstruct[hInner] | (b in l and l in caseConstruct[sw.jumpSet] )  =>  sw not in ((b.jumpSet.~merge & (SwitchBlock -sw)).outerInnerSW)
-- (no ( ( (b.jumpSet.~merge & SwitchBlock) -> sw) & ~outerInnerSW)  )
}


/**
  *  "...a branch from one case construct to another must be for the same OpSwitch"
  *   (The Khronos Group, 2021, p.29)
  *   https://www.khronos.org/registry/spir-v/specs/unified1/SPIRV.pdf
  */
pred NoJumpBetweenCaseConstructs 
{
  all sw: SwitchBlock  | no  (caseConstruct[sw.jumpSet] <:jumpSet:> caseConstruct[(SwitchBlock - sw).jumpSet]  )
}


/**
  *  "...all branches into a construct from reachable Blocks outside the construct
  *   must be to the header Block"
  *   (The Khronos Group, 2021, p.29)
  *   https://www.khronos.org/registry/spir-v/specs/unified1/SPIRV.pdf
  */
pred BranchesBetweenConstructs 
{
	all  lh: LoopHeader     											   | let lc  = loopConstruct[lh], ctc = continueConstruct[lh.continue]	| (some lc  => no (Block - lc)  <: jumpSet :> (lc - lh)) and  (some ctc => no (Block - ctc) <: jumpSet :> (ctc - lh.continue ))   
	all  sh: SelectionHeader 												| let sc  = selectionConstruct[sh]  | some sc  => no (Block - sc)  <: jumpSet :> (sc - sh)
	all  sw_target : (SwitchBlock.jumpSet - SwitchBlock.merge)  | let csc = caseConstruct[sw_target]| some csc => no (Block - csc) <: jumpSet :> (csc - sw_target)
}


/**
  *  "...an OpSwitch Block dominates all its defined case constructs"
  *   (The Khronos Group, 2021, p.29)
  *   https://www.khronos.org/registry/spir-v/specs/unified1/SPIRV.pdf
  */
pred OpSwitchBlockDominatesAllItsCases 
{
	all sw: SwitchBlock  | (sw <:jumpSet:> (Block - sw.merge)) in structurallyDominates
}


/**
  *  "...each case construct has at most one branch to another case construct"
  *   (The Khronos Group, 2021, p.29)
  *   https://www.khronos.org/registry/spir-v/specs/unified1/SPIRV.pdf
*/
pred AtMostOneBranchToAnotherCaseConstruct 
{
	all sw: SwitchBlock, from: sw.jumpSet - sw.merge | let case_construct_from = caseConstruct[from] |																				
															lone case_construct_from  <:jumpSet:> (selectionConstruct[sw] - sw - case_construct_from)
}


/**
  *  "...each case construct is branched to by at most one other case construct"
  *   (The Khronos Group, 2021, p.29)
  *   https://www.khronos.org/registry/spir-v/specs/unified1/SPIRV.pdf
  */
pred CaseConstructBranchedToByAtMostOneOther 
{
	all sw: SwitchBlock, to: sw.jumpSet - sw.merge | let case_construct_to = caseConstruct[to] |																				
															lone (selectionConstruct[sw] - sw - case_construct_to) <:jumpSet:> case_construct_to
}


/**
  *  "...if Target T1 branches to Target T2, or if Target T1 branches to the Default
  *   and the Default branches to Target T2, then T1 must immediately precede T2
  *   in the list of the OpSwitch Target operands"
  *   (The Khronos Group, 2021, p.29)
  *   https://www.khronos.org/registry/spir-v/specs/unified1/SPIRV.pdf
  *
  *
  * 	The above rule is adjusted as follows:
  *  "if Target T1 branches to Target T2, or if Target T1 branches to the Default
  *   and the Default branches to Target T2, then T1 (or the substring - i.e., the
  *	consecutive run - of occurrences of T1 in case of multiple occurrences of T1 )
  *	must immediately precede T2 (or the substring of occurrences of T2 in case of
  *	multiple occurrences of T2) in the list of the OpSwitch Target operands
  *   see https://gitlab.khronos.org/spirv/SPIR-V/-/issues/673
  *
  *  The above rule is further refined so that T1/T2/Default are replaced by 
  *  "the case construct headed by OpSwitch Target T1/T2/Default".
  *  see https://gitlab.khronos.org/spirv/SPIR-V/-/issues/674
  */
pred OrderOfOpSwitchTargetOperands 
{
	-- In the case where a Block is a switch Block then jump[0] is the default Block
	all sw: SwitchBlock, disj T1,T2: sw.jump.rest.elems, t1: caseConstruct[T1] |
																		  (
																				some t1 and some caseConstruct[T2] and
																				(
																					( some t1 <:jumpSet:> T2 ) ||
																							   							(
																															    (some t1 <:jumpSet:>(sw.jump.first)) and
																															    (some caseConstruct[sw.jump.first]<:jumpSet:>T2)
																															 )
																				 )
																			 )
																			 => ( 	idxOf [sw.jump.rest, T2] = lastIdxOf [sw.jump.rest, T1].add[1]
																					&& ((sw.jump.rest).subseq [idxOf [sw.jump.rest, T2], lastIdxOf [sw.jump.rest, T2]]).elems = T2 // this implements the concept of substring
																				  )
}


/**
  *  "The first Block in a function definition is the entry point of that
  *   function and must not be the target of any branch."
  *   (The Khronos Group, 2021, p.35)
  *   https://www.khronos.org/registry/spir-v/specs/unified1/SPIRV.pdf
  */
pred EntryPointIsNotLoopHeader
{
	EntryPoint not in ran[jumpSet]
}


/**
  *  "OpLoopMerge must immediately precede either an OpBranch or OpBranchConditional
  *   instruction. That is, it must be the second-to-last instruction in its Block."
  *   (The Khronos Group, 2021, p.210)
  *   https://www.khronos.org/registry/spir-v/specs/unified1/SPIRV.pdf
  */
pred OpLoopMergeSecondToLast 
{
	{ all l: LoopHeader | (one l<:jump ) or (#(l<:jump) = 2) }
}


/**
  *   "OpSelectionMerge must immediately precede either an OpBranchConditional or
  * .  OpSwitch instruction. That is, it must be the second-to-last instruction in its Block."
  *   (The Khronos Group, 2021, p.211)
  *   https://www.khronos.org/registry/spir-v/specs/unified1/SPIRV.pdf
  */
pred OpSelectionMergeSecondToLast 
{
	{ all s: SelectionHeader - SwitchBlock | #(s<:jump) = 2  }
}


/**
  *   "OpSwitch: Multi-way branch to one of the operand label <id>."
  *   (The Khronos Group, 2021, p.212)
  *   https://www.khronos.org/registry/spir-v/specs/unified1/SPIRV.pdf
  *
  *   Unconditional jumps have at most two successors
  *
  */
pred OutDegree 
{
	{all b: BLOCK  | b in SwitchBlock => some b<:jump else #(b<:jump) <= 2}
}


/**
  *   Restrict when multiple outgoing edges are allowed
  *
  *   A non-header Block B can have 2 successors, C and D, if at least one of the edges B->C and B->D is an exit edge.
  *
  *   For header Blocks we have already established the outdegrees
  */
pred MultipleOutEdges 
{
	all b: BLOCK - HeaderBlock |   (#(b<:jump) >1)  => 
																		 some b<:exitEdge												 										     
}


pred ExitingTheConstruct
{
	{all disj a,b: Block
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
										 b in a.jumpSet 						and 
										 some headOfInnermostConst_a		and   --i.e., a is nested at some construct
										 b not in innermostConstruct_a 	and   --i.e., b is outside the innermost of a
										 (
											 some ((headOfInnermostConst_a.~jumpSet & headOfInnermostConst_b.~jumpSet) & SwitchBlock) //case->case												 
														=>	a in innermostConstr[headOfInnermostConst_a & (HeaderBlock + LoopHeader.continue)]  
										 )
									  )

									   => 

							   			(
												-- Normal exit from a construct: 
		    									(some a <:jumpSet:> (headOfInnermostConst_a.merge & b )  )   or

												-- ...for a continue construct, a normal exit implies that 'a' is the back-edge Block for the loop associated with the continue construct
		    									 (headOfInnermostConst_a 	 in LoopHeader.continue	and some (a & headOfInnermostConst_a.~continue.~backEdge) <:jumpSet:> (headOfInnermostConst_a.~continue.merge & b) )   or

												-- Branching from a back-edge Block to a loop header:
												 (headOfInnermostConst_a in LoopHeader.continue	and some (a & headOfinnermostContinueConst_a.~continue.~backEdge) <:jumpSet:> (headOfinnermostContinueConst_a.~continue & b))	or

												-- Branching to a loop merge from a non back-edge Block: 
												 ( (no a & LoopHeader.~backEdge) and (some headOfInnermostLoop_a & LoopHeader)	and (some innermostContinueConst_a => headOfInnermostLoop_a in innermostContinueConst_a) and  (some a <:jumpSet:> (headOfInnermostLoop_a.merge & b) )  )	or

												-- Branching to a loop continue target from a non back-edge Block: 
												 ( (no a & LoopHeader.~backEdge) and (some headOfInnermostLoop_a & LoopHeader)	and (some innermostContinueConst_a => headOfInnermostLoop_a in innermostContinueConst_a) and  (some a <:jumpSet:> (headOfInnermostLoop_a.continue & b) )  ) or

												-- Branching to a switch merge: 	
												 (some headOfInnermostSW_a and (some innermostContinueConst_a => headOfInnermostSW_a in innermostContinueConst_a) and (some innermostLoopConst_a => headOfInnermostSW_a in innermostLoopConst_a)	and  some a <:jumpSet:> (headOfInnermostSW_a.merge & b))   
		  							   	)							 
	}
}


pred StructurallyAcyclic 
{
	no ^(jumpSet + merge + continue - backEdge) & iden -- the result is structurally acyclic after removing self-loops and back edges
}


/**
  *  Let B be a continue target; suppose that B is not a loop header and let A->B a control flow edge.
  *  Then A is part of the loop associated with B
  *
  *   spirv-val does (unjustifiably) accept edges like the ones in the following GitHub issue:
  *   https://github.com/afd/spirv-control-flow/issues/28
  */
pred BranchToContinue 
{
	{ all l: LoopHeader | l != l.continue => no (BLOCK - loopConstruct[l]) <: jumpSet :> l.continue }
}


pred	 ex {}


pred Valid { 


	BlockStructurallyReachableFromRoot 
	UniqueMergeBlock 
	HeaderBlockStrictlyDominatesItsMergeBlock 
	BackEdgesBranchToLoopHeader 
	OneBackEdgeBranchingToLoopHeader 
	LoopHeaderDominatesContinueTarget 
	ContinueTargetDominatesBackEdge 
	BackEdgePostDominatesContinueTarget 
	ConstructContainsAnotherHeader 
	ValidBreakBlock 
	ValidContinueBlock 
	ValidBranchToOuterOpSwitchMerge 
	InvalidBranchToOuterOpSwitchMerge 
	NoJumpBetweenCaseConstructs 
	BranchesBetweenConstructs 
	OpSwitchBlockDominatesAllItsCases 
	AtMostOneBranchToAnotherCaseConstruct 
	CaseConstructBranchedToByAtMostOneOther 
	OrderOfOpSwitchTargetOperands 
	EntryPointIsNotLoopHeader 
	OpLoopMergeSecondToLast 
	OpSelectionMergeSecondToLast 
	OutDegree 
	MultipleOutEdges 
   ExitingTheConstruct 
	StructurallyAcyclic
   BranchToContinue
}




pred loop_example {
/*
 * This control flow graph is invalid according to  SPIR-V Specification Version 1.5 wording 
 * because the loop headed by b2 has no back edge: edge b4->b2 is not a back edge since b4 is unreachable.
 * In structural semantics, however, this example is deemed valid.
 */
  some disj b1, b2, b3, b4 : Block {
    EntryPoint = b1
    HeaderBlock = b2
    LoopHeader = b2
    SwitchBlock = none
    jump = (b1 -> (0 -> b2))
         + (b2 -> (0 -> b3))
         + (b4 -> (0 -> b2))
    merge = (b2 -> b3)
    continue = (b2 -> b4)
  }
}
test1: run { loop_example && Valid  } for 4 BLOCK


pred invalid_example {
/* 
 * Here the rule: "ConstructContainsAnotherHeader: ..if a construct contains the header block of another construct, 
 * it should also contain that construct's merge block" is violated because b3 (which is a header) 
 * is contained in the continue construct but b4 (the merge of b3) is not.
 */
  some disj b1, b2, b3, b4, b5 : Block {
    EntryPoint = b1
    HeaderBlock = b2 + b3
    LoopHeader = b2
    SwitchBlock = none
    jump = (b1 -> (0 -> b2))
         + (b2 -> (0 -> b3))
         + (b3 -> ((0 -> b2) + (1 -> b5)))
         + (b4 -> (0 -> b5))
    merge = (b2 -> b5)
         + (b3 -> b4)
    continue = (b2 -> b3)
  }
}
test2: run { invalid_example && Valid } for 5 BLOCK 
