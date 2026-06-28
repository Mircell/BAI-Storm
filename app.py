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
            "max_tokens": 150
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

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/test_connection', methods=['POST'])
def test_connection():
    """Test endpoint to check if the AI API is reachable"""
    try:
        data = request.json
        base_url = data.get('base_url', 'http://127.0.0.1:8000/v1')
        api_key = data.get('api_key', 'sk-local')
        model = data.get('model', 'thinking_not_search')

        logger.debug(f"Testing connection to {base_url} with model {model}")

        # Try to list models using a GET request to /models
        models_url = f"{base_url}/models"
        headers = {"Authorization": f"Bearer {api_key}"}
        try:
            resp = requests.get(models_url, headers=headers, timeout=10)
            if resp.status_code == 200:
                models_data = resp.json()
                model_names = [m['id'] for m in models_data.get('data', [])]
                return jsonify({
                    'success': True,
                    'message': 'Connection successful',
                    'models': model_names
                })
            else:
                # If models endpoint fails, try a simple chat completion
                chat_url = f"{base_url}/chat/completions"
                chat_data = {
                    "model": model,
                    "messages": [{"role": "user", "content": "Hello"}],
                    "max_tokens": 5
                }
                resp = requests.post(chat_url, headers=headers, json=chat_data, timeout=10)
                if resp.status_code == 200:
                    return jsonify({
                        'success': True,
                        'message': 'Connection successful (chat endpoint)',
                        'response': resp.json()['choices'][0]['message']['content'][:50]
                    })
                else:
                    return jsonify({
                        'success': False,
                        'error': f'Failed to connect: {resp.status_code} - {resp.text[:100]}'
                    }), 400
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Failed to connect: {str(e)}'
            }), 400
    except Exception as e:
        logger.error(f"Test connection error: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

@app.route('/start', methods=['POST'])
def start_session():
    try:
        data = request.json
        num_agents = int(data.get('num_agents', 3))
        problem = data.get('problem', '')
        base_url = data.get('base_url', 'http://127.0.0.1:8000/v1')
        api_key = data.get('api_key', 'sk-local')
        model = data.get('model', 'thinking_not_search')
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

        return jsonify({
            'status': 'running',
            'agent': agent_name,
            'idea': idea,
            'round': sess.round,
            'agent_index': sess.current_agent_index,
            'total_agents': sess.num_agents,
            'summary': sess.get_summary()
        })
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
        html = render_template('export.html', summary=summary)
        return html
    except Exception as e:
        logger.error(f"Export error: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)