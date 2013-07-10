import libxml2
import libxslt
import sys
import os
import shutil
import MySQLdb

unitOrdinal = 1
lessonOrdinal = 1
objectiveOrdinal = 1

# Open a connection to the MySQL database
db = MySQLdb.connect(host="localhost", user="root", passwd="BUypNP5k", db="jsprogfinal");
cur = db.cursor()
cur.execute("DROP TABLE IF EXISTS units")
cur.execute("CREATE TABLE units (id VARCHAR(255), ordinal INT, title TEXT, PRIMARY KEY(id))")
cur.execute("DROP TABLE IF EXISTS lessons")
cur.execute("CREATE TABLE lessons (id VARCHAR(255), unitid VARCHAR(255), ordinal INT, title TEXT, PRIMARY KEY(id, unitid))")
cur.execute("DROP TABLE IF EXISTS objectives")
cur.execute("CREATE TABLE objectives (id VARCHAR(255), lessonid VARCHAR(255), unitid VARCHAR(255), ordinal INT, title TEXT, PRIMARY KEY(id, lessonid, unitid))")
cur.execute("DROP TABLE IF EXISTS problems")
cur.execute("CREATE TABLE problems (id VARCHAR(255), objectiveid VARCHAR(255), lessonid VARCHAR(255), unitid VARCHAR(255), PRIMARY KEY(id, objectiveid, lessonid, unitid))")
cur.execute("DROP TABLE IF EXISTS questions")
cur.execute("CREATE TABLE questions (id INT, problemid VARCHAR(255), objectiveid VARCHAR(255), lessonid VARCHAR(255), unitid VARCHAR(255), PRIMARY KEY(id, problemid, objectiveid, lessonid, unitid))")
cur.execute("DROP TABLE IF EXISTS answers")
cur.execute("CREATE TABLE answers (id INT, questionid INT, problemid VARCHAR(255), objectiveid VARCHAR(255), lessonid VARCHAR(255), unitid VARCHAR(255), answer text, PRIMARY KEY(id, questionid, problemid, objectiveid, lessonid, unitid))")

def getAttribute (attribute, node):
  currAttr = node.properties;
  while currAttr:
    if currAttr.name == attribute:
      return currAttr.children.content
    currAttr = currAttr.next
  return False

def getId (node):
  return getAttribute ("id", node)

def getAnswer (node):
  return getAttribute ("answer", node)

def getProblemPath (problem):
  # Make sure this is a problem 
  assert (problem.name == "problem")
  # Get the objective's id
  objective = problem.parent.parent
  assert (objective.name == "objective")
  objectiveid = getId(objective)
  assert (objectiveid)
  # Get the lesson's id
  lesson = objective.parent.parent
  assert (lesson.name == "lesson")
  lessonid = getId(lesson)
  assert (lessonid)
  # Get the unit's id
  unit = lesson.parent
  assert (unit.name == "unit")
  unitid = getId(unit)
  assert (unitid)
  # Combine them all to give the problem's full id
  path = os.path.join(unitid, lessonid, objectiveid)
  return path

def checkTest(node):
  currAttr = node.properties;
  while currAttr:
    # print "    " + currAttr.name
    if (currAttr.name == "test" and currAttr.children.content == "false") or (currAttr.name == "hidden" and currAttr.children.content == "true"):
      return False
    currAttr = currAttr.next
  return True

def checkTestProblem (problem):
  # It doesn't really belong here but this is the most convenient place to setup the database tables
  global db, cur, unitOrdinal, lessonOrdinal, objectiveOrdinal
  assert (problem and problem.name == "problem")
  problemid = getId(problem)
  assert(problemid)
  objective = problem.parent.parent
  assert (objective and objective.name == "objective")
  objectiveid = getId(objective)
  objectiveTitle = getAttribute("title", objective)
  assert(objectiveid)
  lesson = objective.parent.parent
  assert (lesson and lesson.name == "lesson")
  lessonid = getId(lesson)
  lessonTitle = getAttribute("title", lesson)
  assert(lessonid)
  unit = lesson.parent
  assert (unit and unit.name == "unit")
  unitid = getId(unit)
  unitTitle = getAttribute("title", unit)
  assert(unitid)
  # Check if we're testing this unit
  if not checkTest(unit): 
    return False
  else:
    if cur.execute("INSERT IGNORE INTO units (id, ordinal, title) VALUES ('" + unitid + "', " + str(unitOrdinal) + ", %s)", unitTitle):
      unitOrdinal = unitOrdinal + 1;
  # Check if we're testing this lesson
  if not checkTest(lesson): 
    return False
  else:
    if cur.execute("INSERT IGNORE INTO lessons (id, unitid, ordinal, title) VALUES ('" + lessonid + "', '" + unitid + "', " + str(lessonOrdinal) + ", %s)", lessonTitle):
      lessonOrdinal = lessonOrdinal + 1;
  # Check if we're testing this objective
  if not checkTest(objective): 
    return False
  else:
    if cur.execute("INSERT IGNORE INTO objectives (id, lessonid, unitid, ordinal, title) VALUES ('" + objectiveid + "', '" + lessonid + "', '" + unitid + "', " + str(objectiveOrdinal) + ", %s)", objectiveTitle):
      objectiveOrdinal = objectiveOrdinal + 1;
  # Check if we're testing this problem itself
  if not checkTest(problem): 
    return False
  else:
    cur.execute("INSERT INTO problems (id, objectiveid, lessonid, unitid) VALUES ('" + problemid + "', '" + objectiveid + "', '" + lessonid + "', '" + unitid + "')")
  # We are testing this problem so first add all the questions and answers into the database
  global course
  problemContext = course.xpathNewContext()
  problemContext.setContextNode(problem)
  questions = problemContext.xpathEval("descendant::*[local-name()='prompt']")
  questionid = 1
  while questionid <= len(questions):
    cur.execute("INSERT INTO questions (id, problemid, objectiveid, lessonid, unitid) VALUES (" + str(questionid) + ", '" + problemid + "', '" + objectiveid + "', '" + lessonid + "', '" + unitid + "')")
    # print ("Inserting " + str(questionid) + " " + problemid + " " + objectiveid + " " + unitid)
    answerid = 0
    answerAttribute = getAnswer(questions[questionid-1])
    if answerAttribute:
      cur.execute("INSERT INTO answers (id, questionid, problemid, objectiveid, lessonid, unitid, answer) VALUES (" + str(answerid) + ", " + str(questionid) + ", '" + problemid + "', '" + objectiveid + "', '" + lessonid + "', '" + unitid + "', '" + answerAttribute + "')")
    answerContext = course.xpathNewContext()
    answerContext.setContextNode(questions[questionid-1])
    answers = answerContext.xpathEval("descendant::*[local-name()='answer']")
    answerid = 1
    while answerid <= len(answers):
      cur.execute("INSERT INTO answers (id, questionid, problemid, objectiveid, lessonid, unitid, answer) VALUES (" + str(answerid) + ", " + str(questionid) + ", '" + problemid + "', '" + objectiveid + "', '" + lessonid + "', '" + unitid + "', '" + answers[answerid-1].children.content + "')")
      answerid += 1
    answerContext.xpathFreeContext()
    questionid += 1
  return True
  problemContext.xpathFreeContext()

testStylesheetDoc = libxml2.parseFile ('./test.xsl')
testStylesheet = libxslt.parseStylesheetDoc (testStylesheetDoc)
validationStylesheetDoc = libxml2.parseFile ('./testvalidation.xsl')
validationStylesheet = libxslt.parseStylesheetDoc (validationStylesheetDoc)
course = libxml2.parseFile ('course.xml')

# Get parameters that get sent to the transformation
siteName = str (course.getRootElement().prop ('name'))
siteTitle = str (course.getRootElement().prop ('title'))
siteAuthor = str (course.getRootElement().prop ('author')) 
siteAuthorEmail = str (course.getRootElement().prop ('authorEmail')) 
siteDomain = str (course.getRootElement().prop ('domain')) 
mainPage = str (course.getRootElement().prop ('mainpage')) 
showSfLogo = str (course.getRootElement().prop ('showsflogo')) 
params = {'type': "'test'", 'siteName': "'" + siteName + "'", 'siteTitle': "'" + siteTitle + "'", 'siteAuthor': "'" + siteAuthor + "'", 'siteAuthorEmail': "'" + siteAuthorEmail + "'", 'siteDomain': "'" + siteDomain + "'", 'showSfLogo': "'" + showSfLogo + "'"}

courseContext = course.xpathNewContext()
problems = courseContext.xpathEval("//*[local-name()='problem']")
for problem in problems: 
  if checkTestProblem(problem):
    problemId = getId(problem)
    assert (problemId)
    path = getProblemPath(problem)
    problemPath = os.path.join('problems', path)
    if not os.path.exists(problemPath):
      os.makedirs(problemPath)
    problemFileName = os.path.join (problemPath, problemId + ".xml")
    problemFile = open(problemFileName, 'w')
    problemFile.write(str(problem))
    problemFile.close()
    problemParsed = libxml2.parseFile (problemFileName)
    problemPageHTML = testStylesheet.applyStylesheet (problemParsed, params)
    testStylesheet.saveResultToFilename (os.path.join (problemPath, problemId + '.html'), problemPageHTML, 0)
    validatePath = os.path.join ('js', path)
    if not os.path.exists(validatePath):
      os.makedirs(validatePath)
    validateFileName = os.path.join (validatePath, problemId + ".js")
    problemPageJS = validationStylesheet.applyStylesheet (problemParsed, params)
    validationStylesheet.saveResultToFilename (validateFileName, problemPageJS, 0)
courseContext.xpathFreeContext()
db.commit()
db.close()
