from mlagents_envs.environment import UnityEnvironment
from mlagents_envs.base_env import DecisionSteps, TerminalSteps, ActionTuple,  ActionSpec, BehaviorSpec, DecisionStep
import numpy as np
class dodgeball_agents:
    def __init__(self,file_name):
        self.file_name = file_name
        self.worker_id = 5
        self.seed = 4
        self.side_channels = []
        self.env=None
        self.nbr_agent=3
        self.spec=None
        self.agent_obs_size = 356 #512##without stacking##
        self.num_envs = 1
        self.num_time_stacks = 3 #as defined in the build
        self.decision_steps = []
        self.terminal_steps = []
        self.agent_ids=([0, 1, 2],[3, 4, 5])
        
    ##return the environment from the file
    def set_env(self):
        self.env=UnityEnvironment(file_name=self.file_name,worker_id=self.worker_id, seed=self.worker_id, side_channels=self.side_channels)
        self.env.reset()
        self.spec=self.team_spec() 
        d0,t0 = self.env.get_steps(self.get_teamName(teamId = 0))
        d1,t1 = self.env.get_steps(self.get_teamName(teamId = 1))
        self.decision_steps.insert(0,d0)
        self.decision_steps.insert(1,d1)
        self.terminal_steps.insert(0,t0)
        self.terminal_steps.insert(1,t1)
        assert len(self.decision_steps[0]) == len(self.decision_steps[1])
        self.nbr_agent=len(self.decision_steps[0])
        if self.num_envs > 1:
            self.agent_ids = ([0, 19, 32],[37, 51, 68]) #(purple, blue) 
        else:
            self.agent_ids = ([0, 1, 2],[3, 4, 5])
        #return self.env
    
    ##specify the behaviour name for the corresponding team,here in this game id is either 0 or 1
    def get_teamName(self,teamId=0):
        assert teamId in [0,1]
        return list(self.env.behavior_specs)[teamId]

    ## define the specification of the observation and actions of the environment
    def team_spec(self):
        return self.env.behavior_specs[self.get_teamName()]

    ## continous and descrete actions
    def action_size(self):
        return self.spec.action_spec
    
    ## observation size in [(3, 8), (738,), (252,), (36,), (378,), (20,)] format
    def obs_size(self):
        return [self.spec.observation_specs[i].shape for i in range(len(self.spec.observation_specs))]

    #close the environment
    def close(self):
        self.env.close()

    ## move the environment to the next step
    def set_step(self):
        self.env.step()
        self.decision_steps[0],self.terminal_steps[0] = self.env.get_steps(self.get_teamName(teamId=0))
        self.decision_steps[1],self.terminal_steps[1] = self.env.get_steps(self.get_teamName(teamId=1))

    ## set the action for each agent of respective team
    def set_action_for_agent(self,teamId,agentId,act_continuous,act_discrete):
        assert type(act_continuous) == np.ndarray and type(act_discrete) == np.ndarray
        assert act_continuous.shape[1] == self.spec.action_spec.continuous_size and act_continuous.shape[0] == 1 \
                and act_discrete.shape[1] == self.spec.action_spec.discrete_size and act_discrete.shape[0] == 1
        action_tuple = ActionTuple()
        action_tuple.add_continuous(act_continuous)
        action_tuple.add_discrete(act_discrete)
        self.env.set_action_for_agent(self.get_teamName(teamId),self.agent_ids[teamId][agentId], action_tuple)

    ##set the action for all agents of the repective team
    def set_action_for_team(self,teamId,act_continuous,act_discrete):
        assert type(act_continuous) == np.ndarray and type(act_discrete) == np.ndarray
        assert act_continuous.shape[1] == self.spec.action_spec.continuous_size and act_continuous.shape[0] == self.nbr_agent \
                and act_discrete.shape[1] == self.spec.action_spec.discrete_size and act_discrete.shape[0] == self.nbr_agent
        action_tuple = ActionTuple()
        action_tuple.add_continuous(act_continuous)
        action_tuple.add_discrete(act_discrete)
        self.env.set_actions(self.get_teamName(teamId),action_tuple)
    
    
    
    ##returns decision step for single agent from decision steps, team_id (0 or 1) and agent_index(0 or 1 or 2)
    def get_agent_decision_step(self,decision_steps, team_id, agent_index):
        assert team_id in [0, 1]
        assert agent_index in range(self.nbr_agent)
        assert type(decision_steps) == DecisionSteps
        return decision_steps[self.agent_ids[team_id][agent_index]]
        
    
    ##given a decision step corresponding to a particular agent, return the observation as a long 1 dimensional numpy array
    def get_agent_obs_with_n_stacks(self, decision_step, num_time_stacks=1):
        #TODO: ainitialize with a big enough result instead of repetitive concatenation
        assert num_time_stacks >= 1
        assert type(decision_step) == DecisionStep
        obs = decision_step.obs
        result = obs[0].reshape((-1,))
        for i in range(1, len(obs)-1):
            result = np.concatenate((result, obs[i][:int(obs[i].shape[0]/self.num_time_stacks*num_time_stacks)]))
        result = np.concatenate((result, obs[-1]))
        return result
    

    ##returns agent observation from team decision_steps
    def get_agent_obs_from_decision_steps(self, decision_steps, team_id, agent_index, num_time_stacks=1):
        decision_step = self.get_agent_decision_step(decision_steps, team_id, agent_index)
        return self.get_agent_obs_with_n_stacks(decision_step, num_time_stacks)
        
        
    ##returns concatenated team observation from team decision_steps
    def get_team_obs_from_decision_steps(self, decision_steps, team_id, num_time_stacks=1):
        team_obs = np.zeros(shape=(self.nbr_agent*self.agent_obs_size,))
        for idx in range(self.nbr_agent):
            team_obs[self.agent_obs_size*idx:self.agent_obs_size*(idx+1)] = self.get_agent_obs_from_decision_steps(decision_steps, team_id, idx, num_time_stacks)
        return team_obs
            
    ##returns agent reward ##    
    def reward(self,team_id,agent_index):
        if self.agent_ids[team_id][agent_index] in self.decision_steps[team_id].agent_id:
            reward = self.decision_steps[team_id].__getitem__(self.agent_ids[team_id][agent_index]).reward
            #done = False
        if self.agent_ids[team_id][agent_index] in self.terminal_steps[team_id].agent_id:
            reward = self.terminal_steps[team_id].__getitem__(self.agent_ids[team_id][agent_index]).reward
            #done = True
        return reward  
    
    ##returns done##
    def terminal(self,team_id,agent_index):
        if self.agent_ids[team_id][agent_index] in self.decision_steps[team_id].agent_id:
        #    reward = self.decision_steps.__getitem__(self.agent_ids[team_id][agent_index]).reward
            done = False
        if self.agent_ids[team_id][agent_index] in self.terminal_steps[team_id].agent_id:
        #    reward = self.terminal_steps.__getitem__(self.agent_ids[team_id][agent_index]).reward
            done = True
        return done 
   
    ##get all agent obs as a list where each element in the list corresponds to an agent's observation##
    def get_all_agent_obs(self):
        obs = []
        for teamid in range(2):
            for agentIndex in range(3):
                obs.append(self.get_agent_obs_from_decision_steps(self.decision_steps[teamid],teamid,agentIndex,1))
        return obs

    ##reset the environment like gym##
    def reset(self):
        self.env.reset()
        self.decision_steps[0],self.terminal_steps[0] = self.env.get_steps(self.get_teamName(teamId = 0))
        self.decision_steps[1],self.terminal_steps[1] = self.env.get_steps(self.get_teamName(teamId = 1))
        return self.get_all_agent_obs()
    
    ##puting the above set_action_for_agent in a convinient way##
#     def set_action_for_agent_(self,teamId,agentInd,action_tuple):
#         self.set_action_for_agent(teamId=teamId,agentId=agentInd,act_continuous=action_tuple.continuous,act_discrete=action_tuple.discrete)
    
    ##get rewards as a list of reward of each agent in the game##
    def get_all_agent_reward(self):
        rewards = []
        for teamId in range(2):
            for agentInd in range(3):
                rewards.append(self.reward(teamId,agentInd))
        return rewards
    
    
    ##get all agent dones as a list of each agent done##
    def get_all_agent_done(self):
        dones = []
        for teamId in range(2):
            for agentInd in range(3):
                dones.append(self.terminal(teamId,agentInd))
        return dones
  
    def numpy_list_to_action_tuple_list(self, numpy_list):
        num_continuous = 3
        action_tuple_list = []
        denormalize_param = 1 #for continuous actions, i.e. 1.0 from network  = 10 in env
        for element in numpy_list:
            action_tuple_continuous = element[:num_continuous]
            action_tuple_discrete = np.random.binomial(1, p=element[num_continuous:])
            action_tuple_list.append([action_tuple_continuous, action_tuple_discrete])
        return action_tuple_list

    ##step equivalent of gym environment##
    ##expects actions to be the list of numpy arrays where each array is of the form
    ## np.array([0.64, 0.78, 0.56, 0.45, 0.89])
    ## first three are normalized continuous actions, last 2 are probabilities of performing the corresponding discrete action
    
    def step(self,actions):
        action_idx = 0
        actions = numpy_list_to_action_tuple_list(actions)

        ##set action for all agents##
        for teamId in range(2):
            for agentInd in range(3):
                action = actions[action_idx]
                self.set_action_for_agent(teamId,agentInd,action[0], action[1])
                action_idx += 1
        
        ##step insimulation##
        self.env.step()
        
        ##get the new decision and terminal steps##
        self.decision_steps[0],self.terminal_steps[0] = self.env.get_steps(self.get_teamName(teamId = 0))
        self.decision_steps[1],self.terminal_steps[1] = self.env.get_steps(self.get_teamName(teamId = 1))
        
        ##get next_states ,rewards and dones from updated decision and terminal steps##
        next_states  = self.get_all_agent_obs()
        rewards = self.get_all_agent_reward()
        dones = self.get_all_agent_done()
        
        return next_states,rewards,dones

##return random action for checking if functionalities are working
    def random_action(self):
        actions = []
        for i in range(6):
            actions.append(self.spec.action_spec.random_action(1))
        return actions

    
        
    
    
            
            
        

