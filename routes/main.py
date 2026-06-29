import logging
import traceback
from flask import Blueprint, render_template, request, jsonify

from models.session import BrainstormSession, SixHatsSession
from services.session_manager import get_session, create_session, stop_session

main_bp = Blueprint('main', __name__)
logger = logging.getLogger(__name__)

@main_bp.route('/')
def index():
    return render_template('main.html')

@main_bp.route('/six-hats')
def six_hats():
    return render_template('six_hats.html')

@main_bp.route('/brainstorm')
def brainstorm():
    return render_template('brainstorm.html')

@main_bp.route('/start', methods=['POST'])
def start_session():
    try:
        data = request.json
        num_agents = int(data.get('num_agents', 3))
        problem = data.get('problem', '')
        base_url = data.get('base_url', 'http://127.0.0.1:8000/v1')
        api_key = data.get('api_key', 'sk-local')
        model = data.get('model', 'llama2')
        personalities = data.get('personalities', [])
        agent_names = data.get('agent_names', [])

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
            personalities=personalities,
            agent_names=agent_names
        )
        session_id = create_session(session_obj)
        logger.debug(f"Session created: {session_id}")
        return jsonify({'session_id': session_id})
    except Exception as e:
        logger.error(f"Start session error: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500

@main_bp.route('/start_six_hats', methods=['POST'])
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
        session_id = create_session(session_obj)
        logger.debug(f"Six hats session created: {session_id}")
        return jsonify({'session_id': session_id})
    except Exception as e:
        logger.error(f"Start six hats session error: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500

@main_bp.route('/next/<session_id>')
def next_idea(session_id):
    try:
        logger.debug(f"Next idea request for session: {session_id}")
        sess = get_session(session_id)
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

@main_bp.route('/stop/<session_id>', methods=['POST'])
def stop_session_route(session_id):
    try:
        if stop_session(session_id):
            sess = get_session(session_id)
            return jsonify({'status': 'stopped', 'summary': sess.get_summary() if sess else {}})
        return jsonify({'error': 'Session not found'}), 404
    except Exception as e:
        logger.error(f"Stop session error: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500

@main_bp.route('/export/<session_id>')
def export_html(session_id):
    try:
        sess = get_session(session_id)
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