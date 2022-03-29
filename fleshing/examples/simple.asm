; SPIR-V
; Version: 1.3
; Generator: Khronos Glslang Reference Front End; 8
; Bound: 15
; Schema: 0
               OpCapability Shader
          %1 = OpExtInstImport "GLSL.std.450"
               OpMemoryModel Logical GLSL450
               OpEntryPoint GLCompute %4 "main"
               OpExecutionMode %4 LocalSize 1 1 1
               OpSource ESSL 320
               OpName %4 "main"

          %2 = OpTypeVoid
          %3 = OpTypeFunction %2
         %11 = OpTypeBool
         %12 = OpConstantTrue %11

          %4 = OpFunction %2 None %3

          %5 = OpLabel
               OpBranch %6

          %6 = OpLabel
               OpLoopMerge %8 %9 None
               OpBranch %10

         %10 = OpLabel
               OpBranchConditional %12 %7 %8

          %7 = OpLabel
               OpSelectionMerge %14 None
               OpBranchConditional %12 %13 %14

         %13 = OpLabel
               OpBranch %14

         %14 = OpLabel
               OpBranch %9

          %9 = OpLabel
               OpBranch %6

          %8 = OpLabel
               OpReturn
               OpFunctionEnd
