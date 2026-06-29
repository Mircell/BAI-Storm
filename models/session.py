import uuid
import requests
import logging
import traceback

logger = logging.getLogger(__name__)

class BrainstormSession:
    def __init__(self, num_agents, problem, base_url, api_key, model, personalities=None, agent_names=None):
        self.session_id = str(uuid.uuid4())
        self.num_agents = num_agents
        self.problem = problem
        self.base_url = base_url
        self.api_key = api_key
        self.model = model
        self.personalities = personalities or [None] * num_agents
        self.agents = []
        for i in range(num_agents):
            name = agent_names[i] if agent_names and i < len(agent_names) and agent_names[i] else f'Agent {i+1}'
            self.agents.append({
                'name': name,
                'personality': self.personalities[i] if i < len(self.personalities) and self.personalities[i] else "You are a creative and thoughtful AI agent. Provide a unique and insightful idea regarding the given problem.",
                'ideas': []
            })
        self.current_agent_index = 0
        self.round = 1
        self.completed = False
        self.stopped = False
        self.all_ideas = []
        self.idea_count = 0

    def get_next_idea(self):
        if self.stopped or self.completed:
            return None, None

        agent = self.agents[self.current_agent_index]
        # Build context: problem + previous ideas (all previous)
        context = f"Problem: {self.problem}\n\n"
        if self.all_ideas:
            context += "Previous ideas (in order):\n"
            for idx, idea in enumerate(self.all_ideas, 1):
                context += f"{idx}. {idea}\n"
        else:
            context += "No previous ideas yet. Be the first to propose a creative solution.\n"

        # Build system prompt from personality
        system_prompt = agent['personality']

        # Build user prompt
        user_prompt = f"{context}\n\nYou are {agent['name']}. Based on the above, propose one new, unique, and practical idea. Keep it concise (1-2 sentences)."

        logger.debug(f"Calling LLM with base_url={self.base_url}, model={self.model}")
        logger.debug(f"System prompt: {system_prompt[:100]}...")
        logger.debug(f"User prompt: {user_prompt[:200]}...")

        # Prepare API request
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.8,
            "max_tokens": 500
        }

        try:
            response = requests.post(url, headers=headers, json=data, timeout=60)
            response.raise_for_status()
            result = response.json()
            idea = result['choices'][0]['message']['content'].strip()
            logger.debug(f"Idea received: {idea[:100]}...")
        except Exception as e:
            error_msg = str(e)
            logger.error(f"LLM Error: {error_msg}")
            logger.error(traceback.format_exc())
            idea = f"[Error generating idea: {error_msg}]"

        # Store idea
        agent['ideas'].append(idea)
        self.all_ideas.append(idea)
        self.idea_count += 1

        # Move to next agent
        self.current_agent_index += 1
        if self.current_agent_index >= self.num_agents:
            self.current_agent_index = 0
            self.round += 1
            # Continue to next round without stopping

        return agent['name'], idea

    def stop(self):
        self.stopped = True

    def get_summary(self):
        return {
            'problem': self.problem,
            'num_agents': self.num_agents,
            'agents': self.agents,
            'all_ideas': self.all_ideas,
            'completed': self.completed,
            'stopped': self.stopped
        }

# Six Thinking Hats specific session
class SixHatsSession:
    HATS = [
        {'name': 'کلاه سفید (White Hat)', 'color': '#f0f0f0', 'emoji': '⚪', 
         'personality': 'You are a data analyst. Focus on available information, facts, statistics, and objective data. Avoid emotional judgments. Present what is known, what is needed, and what is missing.'},
        {'name': 'کلاه قرمز (Red Hat)', 'color': '#e74c3c', 'emoji': '🔴',
         'personality': 'You are an emotional and intuitive thinker. Express your feelings, emotions, and gut reactions to the idea without needing logical justification. Share your hunches and emotional responses.'},
        {'name': 'کلاه سیاه (Black Hat)', 'color': '#2c3e50', 'emoji': '⚫',
         'personality': 'You are a critical thinker. Identify risks, problems, obstacles, and weaknesses in the idea. Point out what could go wrong and why something might not work. Be cautious and skeptical.'},
        {'name': 'کلاه زرد (Yellow Hat)', 'color': '#f1c40f', 'emoji': '🟡',
         'personality': 'You are an optimist. Focus on benefits, opportunities, and positive aspects of the idea. Identify what could go right and how the idea could succeed. Be constructive and forward-looking.'},
        {'name': 'کلاه سبز (Green Hat)', 'color': '#27ae60', 'emoji': '🟢',
         'personality': 'You are a creative innovator. Generate new ideas, alternatives, and creative solutions. Think outside the box. Offer novel perspectives and innovative approaches to the problem.'},
        {'name': 'کلاه آبی (Blue Hat)', 'color': '#2980b9', 'emoji': '🔵',
         'personality': 'You are a facilitator and manager of thinking. Summarize the discussion, organize thoughts, set the thinking agenda, and draw conclusions. Ensure all perspectives have been considered.'}
    ]

    def __init__(self, problem, base_url, api_key, model):
        self.session_id = str(uuid.uuid4())
        self.problem = problem
        self.base_url = base_url
        self.api_key = api_key
        self.model = model
        self.agents = []
        for i, hat in enumerate(self.HATS):
            self.agents.append({
                'name': hat['name'],
                'color': hat['color'],
                'emoji': hat['emoji'],
                'personality': hat['personality'],
                'ideas': []
            })
        self.current_agent_index = 0
        self.completed = False
        self.stopped = False
        self.all_ideas = []
        self.idea_count = 0

    def get_next_idea(self):
        if self.stopped or self.completed:
            return None, None

        agent = self.agents[self.current_agent_index]
        # Build context: problem + previous ideas (all previous)
        context = f"Problem/Idea: {self.problem}\n\n"
        if self.all_ideas:
            context += "Previous perspectives (in order):\n"
            for idx, idea in enumerate(self.all_ideas, 1):
                context += f"{idx}. {idea}\n"
        else:
            context += "No previous perspectives yet. Be the first to provide your analysis.\n"

        # Build system prompt from personality
        system_prompt = agent['personality']

        # Build user prompt
        user_prompt = f"{context}\n\nYou are {agent['name']}. Based on the above, provide your analysis and perspective. Keep it concise (2-3 sentences)."

        logger.debug(f"Calling LLM with base_url={self.base_url}, model={self.model}")
        logger.debug(f"System prompt: {system_prompt[:100]}...")
        logger.debug(f"User prompt: {user_prompt[:200]}...")

        # Prepare API request
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.8,
            "max_tokens": 500
        }

        try:
            response = requests.post(url, headers=headers, json=data, timeout=60)
            response.raise_for_status()
            result = response.json()
            idea = result['choices'][0]['message']['content'].strip()
            logger.debug(f"Idea received: {idea[:100]}...")
        except Exception as e:
            error_msg = str(e)
            logger.error(f"LLM Error: {error_msg}")
            logger.error(traceback.format_exc())
            idea = f"[Error generating idea: {error_msg}]"

        # Store idea
        agent['ideas'].append(idea)
        self.all_ideas.append(idea)
        self.idea_count += 1

        # Move to next agent
        self.current_agent_index += 1
        if self.current_agent_index >= len(self.agents):
            self.current_agent_index = 0
            # Continue to next round without stopping

        return agent['name'], idea

    def stop(self):
        self.stopped = True

    def get_summary(self):
        return {
            'problem': self.problem,
            'agents': self.agents,
            'all_ideas': self.all_ideas,
            'completed': self.completed,
            'stopped': self.stopped
        }