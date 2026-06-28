import os
import json
import time
import uuid
import traceback
import logging
import requests
from flask import Flask, render_template, request, jsonify, session, send_file

# تنظیم لاگینگ
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.urandom(24)

# In-memory session storage (for demo purposes)
sessions = {}

# Global error handler to catch all unhandled exceptions and return JSON
@app.errorhandler(Exception)
def handle_exception(e):
    logger.error(f"Unhandled exception: {traceback.format_exc()}")
    return jsonify({'error': str(e)}), 500

class BrainstormSession:
    def __init__(self, num_agents, problem, base_url, api_key, model, personalities=None):
        self.session_id = str(uuid.uuid4())
        self.num_agents = num_agents
        self.problem = problem
        self.base_url = base_url
        self.api_key = api_key
        self.model = model
        self.personalities = personalities or [None] * num_agents
        self.agents = []
        for i in range(num_agents):
            self.agents.append({
                'name': f'Agent {i+1}',
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

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/six-hats')
def six_hats():
    return render_template('six_hats.html')

@app.route('/start', methods=['POST'])
def start_session():
    try:
        data = request.json
        num_agents = int(data.get('num_agents', 3))
        problem = data.get('problem', '')
        base_url = data.get('base_url', 'http://127.0.0.1:8000/v1')
        api_key = data.get('api_key', 'sk-local')
        model = data.get('model', 'llama2')
        personalities = data.get('personalities', [])

        logger.debug(f"Start session: num_agents={num_agents}, problem={problem[:50]}..., base_url={base_url}, model={model}")

        if not problem:
            return jsonify({'error': 'Problem statement is required'}), 400
        if not api_key:
            return jsonify({'error': 'API key is required'}), 400

        session_obj = BrainstormSession(
            num_agents=num_agents,
            problem=problem,
            base_url=base_url,
            api_key=api_key,
            model=model,
            personalities=personalities
        )
        sessions[session_obj.session_id] = session_obj
        logger.debug(f"Session created: {session_obj.session_id}")
        return jsonify({'session_id': session_obj.session_id})
    except Exception as e:
        logger.error(f"Start session error: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500

@app.route('/start_six_hats', methods=['POST'])
def start_six_hats():
    try:
        data = request.json
        problem = data.get('problem', '')
        base_url = data.get('base_url', 'http://127.0.0.1:8000/v1')
        api_key = data.get('api_key', 'sk-local')
        model = data.get('model', 'llama2')

        logger.debug(f"Start six hats session: problem={problem[:50]}..., base_url={base_url}, model={model}")

        if not problem:
            return jsonify({'error': 'Problem/idea is required'}), 400
        if not api_key:
            return jsonify({'error': 'API key is required'}), 400

        session_obj = SixHatsSession(
            problem=problem,
            base_url=base_url,
            api_key=api_key,
            model=model
        )
        sessions[session_obj.session_id] = session_obj
        logger.debug(f"Six hats session created: {session_obj.session_id}")
        return jsonify({'session_id': session_obj.session_id})
    except Exception as e:
        logger.error(f"Start six hats session error: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500

@app.route('/next/<session_id>')
def next_idea(session_id):
    try:
        logger.debug(f"Next idea request for session: {session_id}")
        sess = sessions.get(session_id)
        if not sess:
            logger.error(f"Session not found: {session_id}")
            return jsonify({'error': 'Session not found'}), 404
        if sess.stopped:
            return jsonify({'status': 'stopped', 'summary': sess.get_summary()})
        if sess.completed:
            return jsonify({'status': 'completed', 'summary': sess.get_summary()})

        agent_name, idea = sess.get_next_idea()
        if agent_name is None:
            return jsonify({'status': 'completed', 'summary': sess.get_summary()})

        # Determine if it's a Six Hats session
        is_six_hats = isinstance(sess, SixHatsSession)
        response_data = {
            'status': 'running',
            'agent': agent_name,
            'idea': idea,
            'summary': sess.get_summary()
        }
        if is_six_hats:
            # Find current agent color and emoji
            for agent in sess.agents:
                if agent['name'] == agent_name:
                    response_data['color'] = agent.get('color', '#000000')
                    response_data['emoji'] = agent.get('emoji', '')
                    break

        return jsonify(response_data)
    except Exception as e:
        logger.error(f"Next idea error: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500

@app.route('/stop/<session_id>', methods=['POST'])
def stop_session(session_id):
    try:
        sess = sessions.get(session_id)
        if not sess:
            return jsonify({'error': 'Session not found'}), 404
        sess.stop()
        return jsonify({'status': 'stopped', 'summary': sess.get_summary()})
    except Exception as e:
        logger.error(f"Stop session error: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500

@app.route('/export/<session_id>')
def export_html(session_id):
    try:
        sess = sessions.get(session_id)
        if not sess:
            return jsonify({'error': 'Session not found'}), 404
        summary = sess.get_summary()
        # Check if it's a Six Hats session
        if isinstance(sess, SixHatsSession):
            html = render_template('export_six_hats.html', summary=summary)
        else:
            html = render_template('export.html', summary=summary)
        return html
    except Exception as e:
        logger.error(f"Export error: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)