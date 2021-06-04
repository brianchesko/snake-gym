from __future__ import division
import argparse

import gym
import gym_snake  # though 'unused', registers itself with gym once imported

from keras.models import Sequential
from keras.layers import Dense, Flatten, Conv2D, Conv3D, Permute, Dropout
from keras.optimizers import RMSprop
import keras.backend as K

from rl.agents.dqn import DQNAgent
from rl.core import Processor
from rl.policy import LinearAnnealedPolicy, EpsGreedyQPolicy
from rl.memory import SequentialMemory
from rl.callbacks import ModelIntervalCheckpoint

import numpy as np
import matplotlib.pyplot as plt

IMAGE_DEPTH = 2
LOSS_PENALTY = 1
WINDOW_LENGTH = 4
BATCH_SIZE = 32
MAX_EPISODE_STEPS = 100
TIME_PENALTY = 1 / MAX_EPISODE_STEPS
ENV_NAME = 'snake-v0'

# agent parameters
GAMMA = 0.9
TRAIN_INTERVAL = 1
TARGET_MODEL_UPDATE = 10000
MAX_STEPS = 2_000_000
WARMUP_STEPS = 50000
DOUBLE_Q = True

# optimizer parameters
LEARNING_RATE = 0.00025


class SnakeProcessor(Processor):
    def process_observation(self, observation):
        return observation.astype('int16')  # saves storage in experience memory

    def process_reward(self, reward):
        return np.clip(reward, -1.0, 1.0)


# precondition: len(data) >= window_size
def avg(data, window_size):
    assert len(data) >= window_size
    out = []
    for i in range(len(data) - window_size + 1):
        out.append(sum(data[i:i+window_size]) / window_size)
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['train', 'test'], default='train')
    parser.add_argument('--weights', type=str, default=None)
    parser.add_argument('--height', type=int, default=8)
    parser.add_argument('--width', type=int, default=8)
    parser.add_argument('--showtraining', type=bool, default=False)
    parser.add_argument('--showtesting', type=bool, default=True)
    parser.add_argument('--testeps', type=int, default=20)

    args = parser.parse_args()

    print('Running Snake RL driver with args:', args)

    board_shape = (args.width, args.height, IMAGE_DEPTH)

    # Get the environment and extract the number of actions.
    env = gym.make(ENV_NAME, show=args.showtraining if args.mode == 'train' else args.showtesting,
                   board_shape=board_shape, loss_penalty=LOSS_PENALTY, time_penalty=TIME_PENALTY)
    nb_actions = env.action_space.n

    # Model based on those in the Keras-RL examples, which are themselves based on Mnih et al's Atari RL paper (2015)
    input_shape = (WINDOW_LENGTH, *board_shape)

    if K.image_data_format() == 'channels_last':
        # (width, height, depth, channels)
        permute_dims = (2, 3, 4, 1)
    elif K.image_data_format() == 'channels_first':
        # (channels, width, height, depth)
        permute_dims = (1, 2, 3, 4)
    else:
        raise RuntimeError('Unknown image_dim_ordering.')

    model = Sequential([
        Permute(permute_dims, input_shape=input_shape),
        Conv3D(32, (2, 2, 2), activation='relu'),
        Conv3D(32, (3, 3, 1), activation='relu'),
        Flatten(),
        Dense(64, activation='relu'),
        Dense(16, activation='relu'),
        Dropout(0.2),
        Dense(nb_actions, activation='linear')
    ])

    print(model.summary())

    processor = SnakeProcessor()
    memory = SequentialMemory(limit=1000000, window_length=WINDOW_LENGTH)
    policy = LinearAnnealedPolicy(EpsGreedyQPolicy(), attr='eps', value_max=1.0, value_min=.35, value_test=.05,
                                  nb_steps=1000000)
    dqn = DQNAgent(model=model, nb_actions=nb_actions, policy=policy, memory=memory, processor=processor,
                   nb_steps_warmup=WARMUP_STEPS, gamma=GAMMA, target_model_update=TARGET_MODEL_UPDATE,
                   train_interval=TRAIN_INTERVAL, delta_clip=1., batch_size=BATCH_SIZE, enable_double_dqn=DOUBLE_Q)
    dqn.compile(RMSprop(learning_rate=LEARNING_RATE), metrics=['mae'])

    if args.mode == 'train':
        weights_filename = 'dqn_{}_weights.h5f'.format(ENV_NAME)
        checkpoint_weights_filename = 'dqn_' + ENV_NAME + '_weights_{step}.h5f'
        callbacks = [ModelIntervalCheckpoint(checkpoint_weights_filename, interval=100000)]
        history = dqn.fit(env, callbacks=callbacks, nb_steps=MAX_STEPS, log_interval=10000,
                          nb_max_episode_steps=MAX_EPISODE_STEPS)

        # After training is done, we save the final weights one more time.
        dqn.save_weights(weights_filename, overwrite=True)

        # turn on the viewability after training if desired
        if args.showtesting and not args.showtraining:
            env.enable_view()

        # Plotting code adapted from https://matplotlib.org/gallery/api/two_scales.html
        # Plot the per-episode rewards and steps on the same plot
        fig, ax1 = plt.subplots()

        plt.title('Reward and episode steps versus episode number [smoothed]')

        plot_color = 'tab:blue'
        plot_slice = slice(0, len(history.epoch), int(len(history.epoch) / 1000))
        epoch_slice = history.epoch[plot_slice]
        ep_reward_slice = history.history['episode_reward'][plot_slice]
        ep_steps_slice = history.history['nb_episode_steps'][plot_slice]

        # average out 10 adjacent data points because data changes wildly from one pt to next but still trends
        average_window_size = 10
        avg_epoch_slice = avg(epoch_slice, average_window_size)
        avg_reward_slice = avg(ep_reward_slice, average_window_size)
        avg_steps_slice = avg(ep_steps_slice, average_window_size)

        ax1.set_xlabel('Episode')
        ax1.set_ylabel('Episode reward', color=plot_color)
        ax1.plot(avg_epoch_slice, avg_reward_slice, color=plot_color)
        ax1.tick_params(axis='y', labelcolor=plot_color)

        ax2 = ax1.twinx()

        plot_color = 'tab:red'
        ax2.set_ylabel('Episode steps', color=plot_color)
        ax2.plot(avg_epoch_slice, avg_steps_slice, color=plot_color)
        ax2.tick_params(axis='y', labelcolor=plot_color)

        fig.tight_layout()

        dqn.test(env, nb_episodes=args.testeps,
                 visualize=False)  # gui visualization is enabled via command line args not here

        plt.show()
    elif args.mode == 'test':
        env.human_visible_speed()
        weights_filename = 'dqn_{}_weights.h5f'.format(ENV_NAME)
        if args.weights:
            weights_filename = args.weights
        dqn.load_weights(weights_filename)
        dqn.test(env, nb_episodes=args.testeps,
                 visualize=True)  # gui visualization is enabled via command line args, not here


if __name__ == '__main__':
    main()
