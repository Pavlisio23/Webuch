from data import db_session
from data.news import News
from data.mathes import Match
from datetime import datetime, date


def main():
    db_session.global_init("db/news_match_teams.db")
    db_sess = db_session.create_session()
    team = News()
    team.title = 'Short: BIT to step in as 9z coach at FiReLEAGUE'
    team.date = datetime(2025, 4, 29)
    team.content = 'Gustavo "yel" Knittel will not travel with 9z to FiReLEAGUE Buenos Aires\
     "due to a health problem," the Argentinian organization has announced. \
     Former MIBR coach Bruno "BIT" Fukuda Lima will step in for yel at the single-day tournament on Friday,\
      where 9z will take on BESTIA in the second semi-final.'
    db_sess.add(team)
    db_sess.commit()


if __name__ == '__main__':
    main()
