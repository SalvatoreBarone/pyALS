import sqlite3

class ALSCatalog:
  def __init__(self, file_name):
    self.__connection = None
    try:
      self.__connection = sqlite3.connect(file_name)
      self.__cursor = self.__connection.cursor()
      print("Database created and successfully connected to SQLite")
      print(sqlite3.version)
      self.__init_db()
    except sqlite3.Error as e:
      print(e)
      exit()

  def get_lut_at_dist(self, spec, dist):
    self.__cursor.execute("select aig from luts where spec = '" + str(spec) + "@" + str(dist) + "';")
    return self.__cursor.fetchone()

  def add_lut(self, spec, aig):
    self.__cursor.execute("insert into luts (spec, aig) values ('" + str(spec) + "', ?)",  sqlite3.Binary(aig))
    self.__connectionn.commit()
    
  def __init_db(self):
    self.__cursor.execute("create table if not exists luts (spec text not null, aig blob not null, primary key (spec));")
    self.__connection.commit()