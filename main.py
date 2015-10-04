# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import requests, json
from multiprocessing.dummy import Pool as ThreadPool
#import language_check
#import pprint
searchDepthThreshold = 10
def wikidataSearch(name):
	result = requests.get('https://www.wikidata.org/w/api.php',params={
	'action':'wbsearchentities',
	'search':name,
	'language':'en',
	'format':'json'
	}).json()['search']
	if result==[]:
		print 'WARNING: No match found.'
		return ''
	return result[0]['title']
claimsCache = {}
def wikidataGetClaims(entityId):
	#print 'Retriving claims for',entityId
	if claimsCache.has_key(entityId):
		return claimsCache[entityId]
	else:
		claims = {}
		for propertyId,v in requests.get('https://www.wikidata.org/w/api.php',params={
		'action':'wbgetclaims',
		'entity':entityId,
		'format':'json'
		}).json()['claims'].items():
			itemIds = []
			for va in v:
				mainSnak = va['mainsnak']
				if mainSnak['datatype']=='wikibase-item':
					try:
						itemId = 'Q'+str(mainSnak['datavalue']['value']['numeric-id'])
					except KeyError:
						#print '[WARNING]No datavalue presented in',mainSnak
						continue
					else:
						itemIds.append(itemId)
			if itemIds!=[]:
				claims[propertyId]=itemIds
		claimsCache[entityId] = claims
		return claims
labelCache = {}
def wikidataGetEntityLabel(entityId):
	if labelCache.has_key(entityId):
		return labelCache[entityId]
	else:
		try:
			label = requests.get('https://www.wikidata.org/w/api.php',params={
					'action':'wbgetentities',
					'props':'labels',
					'ids':entityId,
					'languages':'en',
					'format':'json'
					}).json()['entities'][entityId]['labels']['en']['value']
			labelCache[entityId] = label
			return label
		except:
			return entityId
def naturallyDescribeWithClaims(claimsInList):
	result = ''
	for propertyId,itemId in claimsInList:
		result = result + wikidataGetEntityLabel(propertyId)+' '+\
						wikidataGetEntityLabel(itemId)+'. '
	return result
def convertClaimsFromIdsToLabels(claimsInList):
	result = []
	for propertyId,itemId in claimsInList:
		result += [(wikidataGetEntityLabel(propertyId),
					wikidataGetEntityLabel(itemId))]
	return result
def expandClaimsForLooping(claimsInDict):
	claimsInList = []
	for propertyId,itemIds in claimsInDict.items():
		for itemId in itemIds:
			claimsInList.append((propertyId,itemId))
	return claimsInList
# depthFromA = 0
# depthFromB = 0
# currentPathFromA = []
# currentPathFromB = []
# nodesToCheckFromA = []
# nodesWithKnownShortestPaths = {}
# def stepForwardFromA():
# 	possibleSolution = []
# 	for nodeId in nodesToCheckFromA:
# 		if nodeId in nodesWithKnownShortestPaths.viewkeys():
# 			knownPathToThisNode = nodesWithKnownShortestPaths[nodeId]
# 			if knownPathToThisNode[0][1]==ItemAId:
# 				#This path is found starting from this side.
# 				currentPathFromA = 1
# 				if len(currentPathFromA)<len(knownPathToThisNode):
# 					nodesWithKnownShortestPaths[nodeId] = currentPathFromA
# 			else:
# 				#This shortest path is found from the other side!! Yeahhh!
# 				knownPathToThisNode.reverse()
# 				newSolution = currentPathFromA+knownPathToThisNode
# 				if len(possibleSolution)==0 or len(possibleSolution)>newSolution:
# 					possibleSolution = newSolution
# 	if possibleSolution==[]:
# 		return False
# 	else:
# 		print possibleSolution
# 		return True

try:
	f = open('dump.txt','r')
	knownShortestPathsToTarget = json.loads(f.read())
	f.close()
except:
	print '[ERROR]Cannot read dump file; using Q336 ("science") by default.'
	knownShortestPathsToTarget = {'Q336':[('START','Q336')]}#actually this should be "END" but ...
def explore(testItemId):
	global shortestPaths, nodesOnNextLevel, nodesOnThisLevel, ifFoundAnswer, bestAnswer
	testItemClaims = expandClaimsForLooping(wikidataGetClaims(testItemId))
	#print testItemClaims
	for propertyId,itemId in testItemClaims:
		nodesOnNextLevel.update([itemId])
		newPath = shortestPaths[testItemId]+[(propertyId,itemId)]
		if itemId in knownShortestPathsToTarget.keys():
			print 'SUCCESS!'
			ifFoundAnswer = True
			newAnswer = newPath+knownShortestPathsToTarget[itemId]
			if len(bestAnswer)>len(newAnswer) or len(bestAnswer)==0:
				print 'Updating best answer from', bestAnswer, 'to', newAnswer,'.'
				bestAnswer = newAnswer
			return
			#this may NOT be the shortest, since not all nodes in this depth are checked.
		else: #sadly, we have to go on:
			if shortestPaths.has_key(itemId):
				lengthOfOldPath = len(shortestPaths[itemId])
			else:
				lengthOfOldPath = 99999
			lengthOfNewPath = len(newPath)
			#print 'lengthOfNewPath:',lengthOfNewPath
			if lengthOfOldPath>lengthOfNewPath:
				#then we gotta update it
				shortestPaths[itemId] = newPath
def findPath(ItemAId='Q7802'):#,ItemBId='Q336'):
	global shortestPaths, nodesOnNextLevel, nodesOnThisLevel, ifFoundAnswer, bestAnswer
	shortestPaths = {ItemAId:[('START',ItemAId)]}
	nodesOnThisLevel = set()
	nodesOnNextLevel = set()
	nodesOnNextLevel.update([ItemAId])
	bestAnswer = []
	ifFoundAnswer = False
	levelLimit = 10
	if knownShortestPathsToTarget.has_key(ItemAId):
		print 'Already in cache:',knownShortestPathsToTarget[ItemAId]
		bestAnswer = knownShortestPathsToTarget[ItemAId]
		return knownShortestPathsToTarget[ItemAId]
	else:
		while levelLimit>0 and len(nodesOnNextLevel)>0 and not ifFoundAnswer:
			levelLimit -= 1
			print '[DEBUG]Currently on level',levelLimit,'...'
			nodesOnThisLevel = nodesOnNextLevel
			nodesOnNextLevel = set()
			pool = ThreadPool(200) # Sets the pool size
			results = pool.map(explore, nodesOnThisLevel)
			pool.close()	#close the pool 
			pool.join()		#wait for the work to finish
			#print 'shortestPaths:',shortestPaths
		return [] #timed out :(
def DEBUGdumpTheBSide():
	global knownShortestPathsToTarget
	knownShortestPathsToTarget = {}
	findPath('Q133957')
	f = open('dump.txt','w+')
	f.write(json.dumps(shortestPaths, sort_keys=True))
	f.close()
if __name__=='__main__':
	#findPath('Q7802')
	#print naturallyDescribeWithClaims(bestAnswer)
	from flask import Flask, session, render_template, request, jsonify, redirect, url_for, send_from_directory
	app = Flask(__name__)
	# Sessions variables are stored client side, on the users browser. The content of the variables is encrypted, so users can't
	# actually see it. They could edit it, but again, as the content wouldn't be signed with this hash key, it wouldn't be valid
	# You need to set a secret key (random text) and keep it secret.
	app.secret_key = 'iu4hntvw8h7ft'
	#@app.route('/')
	#def index():
	#	return render_template('index.html')
	@app.route('/run')
	def run():
		userInput = request.args.get('query', '')
		print 'userInput:',userInput
		userInputAsId = wikidataSearch(userInput)
		if userInputAsId=='': #no such thing!
			return jsonify(resultInIds=[], resultInLabels=[], naturalDescription='No such thing.')
		else:
			print 'userInputAsId:',userInputAsId
			findPath(userInputAsId)
			if bestAnswer==[]:
				return jsonify(resultInIds=[], resultInLabels=[], naturalDescription='No relationship found.')
			else:
				return jsonify(resultInIds=bestAnswer, resultInLabels=convertClaimsFromIdsToLabels(bestAnswer), naturalDescription=naturallyDescribeWithClaims(bestAnswer))
	app.run(host="0.0.0.0",port=int("1336"),debug=True,threaded=True)
	##DEBUGdumpTheBSide()
	#Set up the language checker:
	#languageTool = language_check.LanguageTool('en-CA')
	#Fix the language:
	#languageCheckerMatches = languageTool.check(naturalDescription)
	#naturalDescription = language_check.correct(naturalDescription, languageCheckerMatches)
	#print naturalDescription