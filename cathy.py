#!python3
'''
attempt to build a python class to read cathy's .caf file
2017/05/31  got entrydat.cpp from Robert Vasicek rvas01@gmx.net :)
2017/06/02  first reading/struct. conversion from entrydat.cpp
2017/06/03  first complete read of a .caf
            first query functions
			
USAGE

type a full path to your catalog .cat file like :
	from os import getcwd
	pth = getcwd()
	catname = '-Downloads.caf'
	pathcatname = os.path.join(pth,catname)

create a python instance from the catalog :
	from cathy import CathyCat
	cat = CathyCat(pathcatname)

cat.pathcat		# catalogfilename in the cathy's ui
cat.date
cat.device
cat.volume
cat.alias
cat.volumename
cat.serial
cat.comment
cat.freesize
cat.archive
		
cat.elm will contain every element (folder name ot filename)
cat.elm[69] returns a tuple with (date, size, parent folder id, filename)
cat.info[folder id] returns a tuple with folder informations

'''
from os import path as ospath
from struct import calcsize, unpack
from time import ctime
from binascii import b2a_hex

class CathyCat() :

	ulCurrentMagic = 3500410407
	ulMagicBase =     500410407
	ulModus =        1000000000
	sVersion = 8 # got a 7 in the .cpp file you share with me, but got an 8 in my .cat testfile genrated in cathy v2.31.3
	
	delim = b'\x00'
	
	def __init__(self,pathcatname) :
		'''
		read a cathy .caf file
		and import it into a python instance
		'''
		
		try : self.buffer = open(pathcatname,'rb')
		except : return
		
		# m_sVersion - Check the magic
		ul = self.readbuf('L')
		if ul > 0 and ul%CathyCat.ulModus == CathyCat.ulMagicBase : 
			m_sVersion= int(ul/CathyCat.ulModus)
		else :
			self.buffer.close()
			return
		
		if m_sVersion > 2 :
			m_sVersion = self.readbuf('h')
		
		if m_sVersion > CathyCat.sVersion :
			return
		
		# m_timeDate
		m_timeDate = ctime(self.readbuf('L'))
		
		# m_strDevice - Starting version 2 the device is saved
		if m_sVersion >= 2 : 
			m_strDevice = self.readstring()
	
		# m_strVolume, m_strAlias > m_szVolumeName
		m_strVolume = self.readstring()
		m_strAlias = self.readstring()
	
		if len(m_strAlias) == 0 :
			m_szVolumeName = m_strVolume
		else :
			m_szVolumeName = m_strAlias
	
		# m_dwSerialNumber well, odd..
		bytesn = self.buffer.read(4)
		rawsn = b2a_hex(bytesn).decode().upper()
		sn = ''
		while rawsn :
			chunk = rawsn[-2:]
			rawsn = rawsn[:-2]
			sn += chunk
		m_dwSerialNumber = '%s-%s'%(sn[:4],sn[4:])
	
		# m_strComment
		if m_sVersion >= 4  :
			m_strComment = self.readstring()
		
		# m_fFreeSize - Starting version 1 the free size was saved
		if m_sVersion >= 1 : 
			m_fFreeSize = self.readbuf('f') # as megabytes
		else :
			m_fFreeSize = -1 # unknow
			
		# m_sArchive
		if m_sVersion >= 6 :
			m_sArchive = self.readbuf('h')
			if m_sArchive == -1 :
				m_sArchive = 0
				
		self.pathcat = pathcatname		# catalogfilename in the cathy's ui
		self.date = m_timeDate
		self.device = m_strDevice
		self.volume = m_strVolume
		self.alias = m_strAlias
		self.volumename = m_szVolumeName
		self.serial = m_dwSerialNumber
		self.comment = m_strComment
		self.freesize = m_fFreeSize
		self.archive = m_sArchive
		
		self.ptr_path = self.buffer.tell() # pointer from which to parse folder info
		
		# folder information : file count, total size
		m_paPaths = []
		lLen = self.readbuf('l')
		for l in range(lLen) :
			if l==0 or m_sVersion<=3 :
				m_pszName = self.readstring()
				print(m_pszName)
			if m_sVersion >= 3 :
				m_lFiles = self.readbuf('l')
				m_dTotalSize = self.readbuf('d')
			m_paPaths.append( (m_lFiles,m_dTotalSize) )
			
		self.info = m_paPaths
		
		self.ptr_files = self.buffer.tell() # pointer from which to parse elements (file or folders)
		
		# files : date, size, parentfolderid, filename
		# if it's a folder :  date, -thisfolderid, parentfolderid, filename
		m_paFileList = []
		lLen = self.readbuf('l')
		for l in range(lLen) :
			elmdate = ctime(self.readbuf('L'))
			if m_sVersion<=6 :
				# later, won't test for now
				m_lLength = 0
			else :
				# m_lLength = self.buffer.read(8)
				m_lLength = self.readbuf('q')
			m_sPathName = self.readbuf('l')  # in the .cpp I think m_sPathName wants 2 bytes but 4 works for me
			# m_sPathName = self.readbuf('H')
			m_pszName = self.readstring()
			m_paFileList.append((elmdate,m_lLength,m_sPathName,m_pszName))
		
		self.elm = m_paFileList
		
		self.buffer.close()
	
	def catpath(self) :
		'''
		returns an absolute path to the main directory
		handled by this .cat file
		'''
		return self.device + self.volume[2:-1]

	def path(self,elmid) :
		'''
		returns the absolute path of an element
		from its id or its name
		'''
		elmid = self._checkelmid(elmid)
		if type(elmid) == list :
			print('got several answers : %s\nselected the first id.'%elmid)
			elmid = elmid[0]
		
		pths = []
		while True :
			dt,lg,pn,nm = self.elm[elmid]
			pths.append(nm)
			# print(lg,pn,nm) # -368 302 cursors
			if pn == 0 :
				pths.append(self.catpath())
				break
			else :
				for elmid,elm in enumerate(self.elm) :
					if elm[1] == -pn :
						# print('>',elm)
						nm = elm[3]
						break
				else :
					print('error in parenting..')
		pths.reverse()
		return ospath.sep.join(pths)

	def parentof(self,elmid) :
		'''
		returns the parent folder of an element,
		from its id or its name
		'''
		
		elmid = self._checkelmid(elmid)
		if type(elmid) == list :
			print('got several answers : %s\nselected the first id.'%elmid)
			elmid = elmid[0]
		
		dt,lg,pn,nm = self.elm[elmid]
		
		# a 0 parentid means it's the catalog 'root'
		if pn == 0 :
			return self.catpath()
		# parent is a folder, it's id is in the size field, negated
		for i,elm in enumerate(self.elm) :
			if elm[1] == -pn : return elm[3]

	def lookup(self,elmname) :
		'''	
		get an internal id from a file or folder name
		several answers are possible
		'''
		ids = []
		for i,elm in enumerate(self.elm) :
			if elm[3] == elmname : ids.append(i)
		return ids[0] if len(ids) == 1 else ids

	# private
	def _checkelmid(self,elmid) :
		if type(elmid) == str : elmid = self.lookup(elmid)
		return elmid
		
	# private. parser struct. fixed lengths
	def readbuf(self,fmt,nb=False) :
		if not(nb) : nb = calcsize(fmt)
		return unpack(fmt, self.buffer.read(nb))[0]
	
	# private. parser string. arbitrary length. delimited by a 0 at its end
	def readstring(self) :
		chain = ''
		while 1 :
			chr = self.readbuf('s')
			if chr == CathyCat.delim : break
			else : 
				try : chain += chr.decode()
				except : pass
		return chain
	
'''
import os
from cathy import CathyCat
pth = os.getcwd()
catname = '-Downloads.caf'
pathcatname = os.path.join(pth,catname)
cat = CathyCat(pathcatname)

cat.pathcat		# catalogfilename in the cathy's ui
cat.date
cat.device
cat.volume
cat.alias
cat.volumename
cat.serial
cat.comment
cat.freesize
cat.archive

'''
