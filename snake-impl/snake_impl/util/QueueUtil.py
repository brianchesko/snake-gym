import snake_impl.messages.message as Msg


def pop_all_queue_type(queue, msg_type):
    non_type = []
    last_move = None
    while not queue.empty():
        next_action = queue.get()
        if isinstance(next_action, msg_type):
            last_move = next_action
        else:
            non_type.append(next_action)
    for action in non_type:
        queue.put(action)
    return last_move


def pop_all_moves(queue):  # pops all moves from the queue and only returns the last one
    return pop_all_queue_type(queue, Msg.Move)
