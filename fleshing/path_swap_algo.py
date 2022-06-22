# These arrays all have Uniform storage class, so are visible to all threads
direction_x_arr = [] # stores direction choice for block i.
direction_x_index_arr = [] # Stores each threads index into the directions_x_arr
output_arr = []
output_index_arr = []
path_swaps = [] 


in entry_block:
    thread_id = (workgroup_id * num_threads_per_workgroup) + local_thread_id
    current_thread_id = thread_id
    swap_index = thread_id * num_barrier_visits
    directions_x_index = direction_x_index_arr[thread_id] # This is thread local
    output_index = output_index_arr[thread_id]
    OpControlBarrier # Workgroup scope and Uniform memory barrier
    output_arr[output_index] = block_id
    output_index += 1

in not entry_block and not return_blocks:

    if block_x.has_barrier():
        direction_x_index_arr[current_thread_id] = directions_x_index
        output_index_arr[current_thread_id] = output_index
        OpControlBarrier # Workgroup scope and Uniform memory barrier
        current_thread_id = path_swaps[swap_index] # Follow the path of the new thread_id
        swap_index += 1
        directions_x_index = direction_x_index_arr[current_thread_id]
        output_index = output_index_arr[current_thread_id]
        OpControlBarrier # Workgroup scope and Uniform memory barrier
    
    output_arr[output_index] = block_id
    output_index += 1
    if block_x.is_conditional():
        directions_x_index += 1

in return_block:
    # Directions and output code execute first
    output_arr[output_index] = block_id
    output_index += 1
    if block_x.is_conditional():
        directions_x_index += 1

    OpControlBarrier # Workgroup scope and Uniform memory barrier
    direction_x_index_arr[current_thread_id] = directions_x_index
    output_index_arr[current_thread_id] = output_index

