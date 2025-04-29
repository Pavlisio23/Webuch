import flask
from . import db_session
from .teams import Team

blueprint = flask.Blueprint(
    'teams_api',
    __name__,
    template_folder='templates'
)


@blueprint.route('/api/teams/')
def get_teams():
    db_sess = db_session.create_session()
    teams = db_sess.query(Team).all()
    return flask.jsonify(
        {
            'team':
                [item.to_dict() for item in teams]
        }
    )


@blueprint.route('/api/teams/<int:team_id>', methods=['GET'])
def get_one_jobs(team_id):
    db_sess = db_session.create_session()
    team = db_sess.query(Team).get(team_id)
    if not team:
        return flask.make_response(flask.jsonify({'error': 'Not found'}), 404)
    return flask.jsonify(
        {
            'team': team.to_dict()
        }
    )
