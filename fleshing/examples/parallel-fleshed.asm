; SPIR-V
; Version: 1.3
; Generator: Khronos Glslang Reference Front End; 8
; Bound: 15
; Schema: 0
               OpCapability Shader
          %1 = OpExtInstImport "GLSL.std.450"
               OpMemoryModel Logical GLSL450
               OpEntryPoint GLCompute %4 "main" %local_invocation_idx_var
               OpExecutionMode %4 LocalSize 3 2 1 ; This is the workgroup size in the x, y and z dimensions.
               OpSource ESSL 320
               OpName %4 "main"

               ; Below, we declare various types and variables for storage buffers.
               ; These decorations tell SPIR-V that the types and variables relate to storage buffers

               OpDecorate %directions_7_struct_type BufferBlock
               OpMemberDecorate %directions_7_struct_type 0 Offset 0
               OpDecorate %directions_7_array_type ArrayStride 4
               OpDecorate %directions_7_variable DescriptorSet 0
               OpDecorate %directions_7_variable Binding 0

               OpDecorate %directions_10_struct_type BufferBlock
               OpMemberDecorate %directions_10_struct_type 0 Offset 0
               OpDecorate %directions_10_array_type ArrayStride 4
               OpDecorate %directions_10_variable DescriptorSet 0
               OpDecorate %directions_10_variable Binding 1

               OpDecorate %output_struct_type BufferBlock
               OpMemberDecorate %output_struct_type 0 Offset 0
               OpDecorate %output_array_type ArrayStride 4
               OpDecorate %output_variable DescriptorSet 0
               OpDecorate %output_variable Binding 2

               OpDecorate %local_invocation_idx_var BuiltIn LocalInvocationIndex

          %2 = OpTypeVoid
          %3 = OpTypeFunction %2
         %11 = OpTypeBool
         %12 = OpConstantTrue %11

   %int_type = OpTypeInt 32 0

 %constant_0 = OpConstant %int_type 0
 %constant_1 = OpConstant %int_type 1
 %constant_5 = OpConstant %int_type 5
 %constant_6 = OpConstant %int_type 6
 %constant_7 = OpConstant %int_type 7
 %constant_8 = OpConstant %int_type 8
 %constant_9 = OpConstant %int_type 9
%constant_10 = OpConstant %int_type 10
%constant_13 = OpConstant %int_type 13
%constant_14 = OpConstant %int_type 14
%constant_256 = OpConstant %int_type 256
 %constant_2 = OpConstant %int_type 2
 %constant_3 = OpConstant %int_type 3
%constant_15 = OpConstant %int_type 15
%path_length = OpConstant %int_type 16
%input_7_length = OpConstant %int_type 12
%input_10_length = OpConstant %int_type 18
%output_length = OpConstant %int_type 96

               ; Added: declaration of three storage buffers, for the directions and the output

%directions_7_array_type = OpTypeArray %int_type %input_7_length
%directions_7_struct_type = OpTypeStruct %directions_7_array_type
%directions_7_pointer_type = OpTypePointer Uniform %directions_7_struct_type
%directions_7_variable = OpVariable %directions_7_pointer_type Uniform

%directions_10_array_type = OpTypeArray %int_type %input_10_length
%directions_10_struct_type = OpTypeStruct %directions_10_array_type
%directions_10_pointer_type = OpTypePointer Uniform %directions_10_struct_type
%directions_10_variable = OpVariable %directions_10_pointer_type Uniform

%output_array_type = OpTypeArray %int_type %output_length
%output_struct_type = OpTypeStruct %output_array_type
%output_pointer_type = OpTypePointer Uniform %output_struct_type
%output_variable = OpVariable %output_pointer_type Uniform

%local_int_ptr = OpTypePointer Function %int_type
%private_local_int_ptr = OpTypePointer Workgroup %int_type

%storage_buffer_int_ptr = OpTypePointer Uniform %int_type
%private_output_index = OpVariable %private_local_int_ptr Workgroup

%input_int_ptr = OpTypePointer Input %int_type

%local_invocation_idx_var = OpVariable %input_int_ptr Input

          %4 = OpFunction %2 None %3

          %5 = OpLabel
%output_index = OpVariable %local_int_ptr Function %constant_0
%directions_7_index = OpVariable %local_int_ptr Function %constant_0
%directions_10_index = OpVariable %local_int_ptr Function %constant_0
               OpControlBarrier %constant_2 %constant_2 %constant_256 ; barrier instruction with Workgroup scope and Workgroup memory semantics

%local_invocation_idx = OpLoad %int_type %local_invocation_idx_var
%directions_7_offset = OpIMul %int_type %local_invocation_idx %constant_2
%directions_10_offset = OpIMul %int_type %local_invocation_idx %constant_3
%output_offset = OpIMul %int_type %local_invocation_idx %path_length
               OpStore %directions_7_index %directions_7_offset
               OpStore %directions_10_index %directions_10_offset
               OpStore %output_index %output_offset

   %temp_5_0 = OpLoad %int_type %output_index
   %temp_5_1 = OpAccessChain %storage_buffer_int_ptr %output_variable %constant_0 %temp_5_0
               OpStore %temp_5_1 %constant_5
   %temp_5_2 = OpIAdd %int_type %temp_5_0 %constant_1
               OpStore %output_index %temp_5_2
               OpStore %temp_5_1 %constant_5
               OpBranch %6

          %6 = OpLabel
   %temp_6_0 = OpLoad %int_type %output_index
   %temp_6_1 = OpAccessChain %storage_buffer_int_ptr %output_variable %constant_0 %temp_6_0
               OpStore %temp_6_1 %constant_6
   %temp_6_2 = OpIAdd %int_type %temp_6_0 %constant_1
               OpStore %output_index %temp_6_2
               OpLoopMerge %8 %9 None
               OpBranch %10

         %10 = OpLabel
  %temp_10_0 = OpLoad %int_type %output_index
  %temp_10_1 = OpAccessChain %storage_buffer_int_ptr %output_variable %constant_0 %temp_10_0
               OpStore %temp_10_1 %constant_10
  %temp_10_2 = OpIAdd %int_type %temp_10_0 %constant_1
               OpStore %output_index %temp_10_2
               ; Look up %directions_10_variable to decide which way to go
               ; Load the current index into the directions_10 array
  %temp_10_3 = OpLoad %int_type %directions_10_index
               ; Get a pointer to this element of the array
  %temp_10_4 = OpAccessChain %storage_buffer_int_ptr %directions_10_variable %constant_0 %temp_10_3
               ; Load the direction from the array
  %temp_10_5 = OpLoad %int_type %temp_10_4 
               ; Compare the loaded direction with the constant 1
  %temp_10_6 = OpIEqual %11 %temp_10_5 %constant_1
               ; Increment the direction index and store it back to its variable
  %temp_10_7 = OpIAdd %int_type %temp_10_3 %constant_1
               OpStore %directions_10_index %temp_10_7
               OpBranchConditional %temp_10_6 %7 %8

          %7 = OpLabel
               ; Similar to the instructions in block %5
   %temp_7_0 = OpLoad %int_type %output_index
   %temp_7_1 = OpAccessChain %storage_buffer_int_ptr %output_variable %constant_0 %temp_7_0
               OpStore %temp_7_1 %constant_7
   %temp_7_2 = OpIAdd %int_type %temp_7_0 %constant_1
               OpStore %output_index %temp_7_2
               ; Similar to the instructions in block %10, for deciding in which direction to go
   %temp_7_3 = OpLoad %int_type %directions_7_index
   %temp_7_4 = OpAccessChain %storage_buffer_int_ptr %directions_7_variable %constant_0 %temp_7_3
   %temp_7_5 = OpLoad %int_type %temp_7_4 
   %temp_7_6 = OpIEqual %11 %temp_7_5 %constant_1
   %temp_7_7 = OpIAdd %int_type %temp_7_3 %constant_1
               OpStore %directions_7_index %temp_7_7
               OpSelectionMerge %14 None
               OpBranchConditional %temp_7_6 %13 %14

         %13 = OpLabel
               ; Similar to the instructions in block %5
  %temp_13_0 = OpLoad %int_type %output_index
  %temp_13_1 = OpAccessChain %storage_buffer_int_ptr %output_variable %constant_0 %temp_13_0
               OpStore %temp_13_1 %constant_13
  %temp_13_2 = OpIAdd %int_type %temp_13_0 %constant_1
               OpStore %output_index %temp_13_2
               OpBranch %14

         %14 = OpLabel
               ; Similar to the instructions in block %5
  %temp_14_0 = OpLoad %int_type %output_index
  %temp_14_1 = OpAccessChain %storage_buffer_int_ptr %output_variable %constant_0 %temp_14_0
               OpStore %temp_14_1 %constant_14
  %temp_14_2 = OpIAdd %int_type %temp_14_0 %constant_1
               OpStore %output_index %temp_14_2
               OpBranch %9

          %9 = OpLabel
               ; Similar to the instructions in block %5
   %temp_9_0 = OpLoad %int_type %output_index
   %temp_9_1 = OpAccessChain %storage_buffer_int_ptr %output_variable %constant_0 %temp_9_0
               OpStore %temp_9_1 %constant_9
   %temp_9_2 = OpIAdd %int_type %temp_9_0 %constant_1
               OpStore %output_index %temp_9_2
               OpBranch %6

          %8 = OpLabel
               ; Similar to the instructions in block %5
   %temp_8_0 = OpLoad %int_type %output_index
   %temp_8_1 = OpAccessChain %storage_buffer_int_ptr %output_variable %constant_0 %temp_8_0
               OpStore %temp_8_1 %constant_8
   %temp_8_2 = OpIAdd %int_type %temp_8_0 %constant_2 ; For the last block, double increment the output idx
               OpStore %output_index %temp_8_2
               OpReturn

               OpFunctionEnd