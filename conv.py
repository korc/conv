#!/usr/bin/python

version=(0,1,0,20100115)

import sys,os,subprocess
sys.path.append(os.path.join(os.path.dirname(sys.argv[0]),'lib'))
sys.path.append(os.path.join(os.path.dirname(sys.argv[0]),'..','lib'))

import tempfile,codecs,re,errno,getopt

class CommandExecutionException(Exception): pass
class NasmException(CommandExecutionException): pass

def str_list_replace(s,pat,repl):
	if type(s)==str:
		return s.replace(pat,repl)
	elif type(s)==list:
		for idx,x in enumerate(s):
			if x==pat: s[idx]=repl
	return s

def pipe_command(command,input=""):
	in_file=out_file=None
	errmsg=''
	if '%i' in command:
		(in_fd,in_file)=tempfile.mkstemp()
		command=str_list_replace(command,'%i',in_file)
		os.write(in_fd,input)
		os.close(in_fd)
	if '%o' in command:
		(out_fd,out_file)=tempfile.mkstemp()
		command=str_list_replace(command,'%o',out_file)
		os.close(out_fd)

	if sys.platform=='win32': command=' '.join(command)
	(cmd_in,cmd_out)=os.popen4(command)
	if in_file is None: cmd_in.write(input)
	cmd_in.close()
	if out_file is None: out=cmd_out.read()
	else: errmsg=cmd_out.read()
	cmd_out.close()
	if out_file is not None:
		out=open(out_file).read()
		try: os.unlink(out_file)
		except OSError,e:
			if e.errno==errno.ENOENT: errmsg+='Outfile deleted.'
			else: raise
	if in_file is not None: os.unlink(in_file)
	if errmsg!='':
		raise CommandExecutionException,errmsg
	return out

def nasm_encode(input,errors='strict'):
	assert errors=='strict'

	(asm_fd,asm_name)=tempfile.mkstemp(suffix='.asm')
	os.write(asm_fd,input)
	os.close(asm_fd)
	(bin_fd,bin_name)=tempfile.mkstemp(suffix='.bin')
	msg=pipe_command(['nasm','-s','-o',bin_name,'-f','bin','--',asm_name])
	os.unlink(asm_name)
	ret=os.read(bin_fd,os.fstat(bin_fd).st_size)
	os.close(bin_fd)
	try: os.unlink(bin_name)
	except OSError,e:
		if e.errno==errno.ENOENT: msg+='compile error.'
		else: raise
	if msg!='':
		raise NasmException,msg
	return (ret,len(input))

def nasm_decode(input,errors='strict'):
	proc=subprocess.Popen(["ndisasm","-i","-u","-"],stdin=subprocess.PIPE,stdout=subprocess.PIPE)
	proc.stdin.write(input)
	proc.stdin.close()
	return (proc.stdout.read(),len(input))

ws_re=re.compile(r'^\[0-9a-f]+  (?P<hex>([0-9a-f]{2} ){16}).*',re.I)
def ws_decode(input,errors='strict'):
	for l in input.split('\n'):
		pass

class NasmCodec(codecs.Codec):
	def encode(self,input,errors='strict'): return nasm_encode(input,errors)
	def decode(self,input,errors='strict'): return nasm_decode(input,errors)
class NasmReader(NasmCodec,codecs.StreamReader): pass
class NasmWriter(NasmCodec,codecs.StreamWriter): pass

def query_encode(input,errors='strict'):
	assert errors=='strict'
	return (re.sub(r'[^\w]',lambda x: '%%%02x'%(ord(x.group(0))),input),len(input))
def query_decode(input,errors='strict'):
	assert errors=='strict'
	return (re.sub(r'%([0-9a-fA-F][0-9a-fA-F])',lambda x: chr(int(x.group(1),16)),input.replace('+',' ')),len(input))
class QueryCodec(codecs.Codec):
	def encode(self,input,errors='strict'): return query_encode(input,errors)
	def decode(self,input,errors='strict'): return query_decode(input,errors)
class QueryReader(QueryCodec,codecs.StreamReader): pass
class QueryWriter(QueryCodec,codecs.StreamWriter): pass

def fullutf7_encode(input,errors='strict'):
	assert errors=='strict'
	return (re.sub(r'[^\w]+',lambda x: '+'+x.group(0).encode('utf-16-be').encode('base64')[:-1].replace('=','')+'-',input),len(input))
def fullutf7_decode(input,errors='strict'):
	return (input.decode('utf7',errors),len(input))
class FullUTF7Codec(codecs.Codec):
	def encode(self,input,errors='strict'): return fullutf7_encode(input,errors)
	def decode(self,input,errors='strict'): return fullutf7_decode(input,errors)
class FullUTF7Reader(FullUTF7Codec,codecs.StreamReader): pass
class FullUTF7Writer(FullUTF7Codec,codecs.StreamWriter): pass



def bin_encode(input,errors='strict'):
	assert errors=='strict'
	return (' '.join([''.join([['1','0'][((1<<(7-x))&ord(c))==0] for x in range(8)]) for c in input]),len(input))
def bin_decode(input,errors='strict'):
	return (''.join([chr(int(v,2)) for v in input.split()]),len(input))
class BinCodec(codecs.Codec):
	def encode(self,input,errors='strict'): return bin_encode(input,errors)
	def decode(self,input,errors='strict'): return bin_decode(input,errors)
class BinReader(BinCodec,codecs.StreamReader): pass
class BinWriter(BinCodec,codecs.StreamWriter): pass

def rbin_encode(input,errors='strict'):
	assert errors=='strict'
	return (' '.join([''.join([['1','0'][((1<<(x))&ord(c))==0] for x in range(8)]) for c in input]),len(input))
def rbin_decode(input,errors='strict'):
	return (''.join([chr(int(''.join(reversed(v)),2)) for v in input.split()]),len(input))
class RBinCodec(codecs.Codec):
	def encode(self,input,errors='strict'): return rbin_encode(input,errors)
	def decode(self,input,errors='strict'): return rbin_decode(input,errors)
class RBinReader(RBinCodec,codecs.StreamReader): pass
class RBinWriter(RBinCodec,codecs.StreamWriter): pass

def codec_reg(name):
	if name=='nasm':
		return (nasm_encode,nasm_decode,NasmReader,NasmWriter)
	elif name=='query':
		return (query_encode,query_decode,QueryReader,QueryWriter)
	elif name=='fullutf7':
		return (fullutf7_encode,fullutf7_decode,FullUTF7Reader,FullUTF7Writer)
	elif name=='bin':
		return (bin_encode,bin_decode,BinReader,BinWriter)
	elif name=='rbin':
		return (rbin_encode,rbin_decode,RBinReader,RBinWriter)

def reg(): codecs.register(codec_reg)

class GUI(object):
	def __getattribute__(self,key):
		try: return object.__getattribute__(self,key)
		except AttributeError,e:
			print '%s __getattribute__: %s'%(self,key)
			raise
	def __init__(self):
		self.ui=gtkutil.GtkBuilderHelper(os.path.join(os.path.split(sys.argv[0])[0],'conv.ui'),self)

		self.rcfile=os.path.expanduser(os.path.join('~','.convert_guirc'))

		self.in_buf=self.ui.intext.get_buffer()
		self.in_buf.connect('changed',self.schedule_change)
		self.update_tmout=None
		self.sbctx=self.ui.sbar.get_context_id(__name__)
		self.sbstack=[]
		self.convstack=[]

		codecs.register(codec_reg)

		font=pango.FontDescription('terminus,fixed,monospace')
		self.ui.intext.modify_font(font)
		self.ui.outtext.modify_font(font)

	def schedule_change(self,*args):
		if self.update_tmout is not None:
			gobject.source_remove(self.update_tmout)
		self.update_tmout=gobject.timeout_add(300,self.do_update_change)

	def on_addbtn_clicked(self,btn):
		self.add_conv()
	
	def on_addconv(self,*args):
		self.add_conv()

	def add_conv(self,is_active=False,is_enc=True,encname=''):
		hbox=gtk.HBox()
		actbtn=gtk.CheckButton('Act')
		actbtn.set_active(is_active)
		actbtn.connect('toggled',self.schedule_change)
		hbox.pack_start(actbtn,expand=False)
		encbtn=gtk.CheckButton('Enc')
		encbtn.set_active(is_enc)
		encbtn.connect('toggled',self.schedule_change)
		hbox.pack_start(encbtn,expand=False)
		entry=gtk.Entry()
		entry.set_text(encname)
		entry.connect('activate',self.schedule_change)
		entry.connect('focus_out_event',self.schedule_change)
		hbox.pack_start(entry)
		img=gtk.Image()
		img.set_from_stock('gtk-stop',gtk.ICON_SIZE_MENU)
		hbox.pack_start(img,expand=False)
		for stock,func in [('gtk-remove',self.on_conv_remove),('gtk-go-up',self.on_conv_moveup),('gtk-go-down',self.on_conv_movedown)]:
			btn=gtk.Button(stock=stock)
			btn.connect('clicked',func,hbox)
			hbox.pack_start(btn,expand=False)
		self.ui.convbox.pack_start(hbox,expand=False)
		hbox.show_all()
		img.hide()
		self.convstack.append(dict(act=actbtn,enc=encbtn,entry=entry,hbox=hbox,stopimg=img))

	def on_fileentry_activate(self,entry):
		print "on_fileentry_activate:",entry.get_text()
		self.load_settings(entry.get_text())

	def on_filechooserbutton_act(self,*args):
		print "on_filechooserbutton_act:",args

	def on_conv_moveup(self,btn,hbox):
		for idx,conv in enumerate(self.convstack):
			if conv['hbox'] is hbox:
				if idx==0: return
				self.ui.convbox.reorder_child(hbox,self.ui.convbox.child_get_property(hbox,'position')-1)
				self.convstack.pop(idx)
				self.convstack.insert(idx-1,conv)
				break
	def on_conv_movedown(self,btn,hbox):
		for idx,conv in enumerate(self.convstack):
			if conv['hbox'] is hbox:
				if idx==len(self.convstack)-1: return
				self.ui.convbox.reorder_child(hbox,self.ui.convbox.child_get_property(hbox,'position')+1)
				self.convstack.pop(idx)
				self.convstack.insert(idx+1,conv)
				break
	def on_conv_remove(self,btn,hbox):
		for conv in self.convstack:
			if conv['hbox'] is hbox:
				self.convstack.remove(conv)
		hbox.destroy()
		self.schedule_change()

	def do_update_change(self):
		self.update_tmout=None
		text=self.in_buf.get_text(self.in_buf.get_start_iter(),self.in_buf.get_end_iter())
		for conv in self.convstack:
			conv['stopimg'].hide()
			if not conv['act'].get_active(): continue
			name=conv['entry'].get_text()
			if name:
				try:
					if name.startswith('!'): text=pipe_command(name[1:],text)
					elif conv['enc'].get_active(): text=text.encode(name)
					else: text=text.decode(name)
				except Exception,e:
					conv['stopimg'].show()
					self.sbstack.append(self.ui.sbar.push(self.sbctx,str(e)))
					return False
		try: text=text.encode('utf8')
		except UnicodeDecodeError,e:
			for conv in reversed(self.convstack):
				if conv['entry'].get_text()=='string_escape':
					if conv['enc'].get_active()==True:
						conv['act'].set_active(True)
						return True
					else: break
				elif conv['act'].get_active(): break
			self.add_conv(True,True,'string_escape')
			return True
		self.ui.outtext.get_buffer().set_text(text)
		for x in self.sbstack: self.ui.sbar.remove(self.sbctx,x)
		return False

	def on_conv_changed(self,*args):
		self.schedule_change()

	def load_settings(self,fname):
		try:
			rcfile=open(fname)
			while 1:
				line=rcfile.readline()
				if line=='': break
				if line.strip()=='---':
					self.ui.intext.get_buffer().set_text(rcfile.read())
					break
				act,enc,name=line.strip().split(',',2)
				self.add_conv(act=='True',enc=='True',name)
		except IOError: pass
	def save_settings(self,fname):
		try: open(fname,'w').write(''.join(['%s,%s,%s\n'%(x['act'].get_active(),x['enc'].get_active(),x['entry'].get_text()) for x in self.convstack])+'---\n'+self.in_buf.get_text(self.in_buf.get_start_iter(),self.in_buf.get_end_iter()))
		except IOError: pass
	def run(self):
		self.load_settings(self.rcfile)
		self.ui.mainwin.connect('destroy',gtk.main_quit)
		gtk.main()
		self.save_settings(self.rcfile)


if __name__=='__main__':
	if len(sys.argv)==1:
		from krutils import gtkutil
		import gtk,gobject,pango
		GUI().run()
	else:
		reg()
		(opts,args)=getopt.getopt(sys.argv[1:],'e:d:')
		if not args: text=sys.stdin.read()
		else: text=open(args[0],'rb').read()
		for opt,optarg in opts:
			if opt=='-e': text=text.encode(optarg)
			if opt=='-d': text=text.decode(optarg,'replace')
		sys.stdout.write(text)
