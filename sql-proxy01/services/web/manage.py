from flask.cli import FlaskGroup

from fs_proxy import app #, db, User
from fs_proxy.db import db
from fs_proxy.models import Esi
import logging

cli = FlaskGroup(app)

@cli.command("create_db")
def create_db():
    try:
        count = Esi.query.count()
        logging.debug("La base de datos ya fue creada "+str(count))
    except:    
        logging.debug("La base de datos no existe. Se procede a crear entidades")
        db.drop_all()
        db.create_all()
        db.session.commit()

if __name__ == "__main__":
    cli()
