from kodi_six import xbmc, xbmcaddon, xbmcgui, xbmcvfs, xbmcplugin
from kodi_six.utils import py2_encode, py2_decode
from contextlib import closing
import os, requests, json, re, routing
import requests.packages.urllib3
requests.packages.urllib3.disable_warnings() #Silence uneeded warnings
plugin_handle = routing.Plugin() #Plugin Handle
# xbmcplugin.setContent(plugin_handle.handle,'movies')

def copy_directory_contents_xbmcvfs(directory_from,directory_to):
	overall_success = True
	files_out = list()
	dirs_in_dir, files_in_dir = xbmcvfs.listdir(os.path.join(directory_from,''))
	for ff in files_in_dir:
		if not xbmcvfs.copy(os.path.join(directory_from,ff),os.path.join(directory_to,ff)): #If move does not work, then copy
			overall_success = False
		else:
			xbmc.log(msg='Retro BIOS Tool:  The file was copied from: %(file_from)s, to: %(file_to)s' % {'file_from': os.path.join(directory_from,ff), 'file_to': os.path.join(directory_to,ff)}, level=xbmc.LOGDEBUG)
			files_out.append(os.path.join(directory_to,ff))
	for dd in dirs_in_dir:
		if xbmcvfs.exists(os.path.join(directory_to,dd,'')) or xbmcvfs.mkdir(os.path.join(directory_to,dd)):
			files_out2, success = copy_directory_contents_xbmcvfs(os.path.join(directory_from,dd),os.path.join(directory_to,dd))
			files_out = files_out + files_out2
		else:
			overall_success = False
	return files_out, overall_success

@plugin_handle.route('/')
def rbt_main():
	# WIN = xbmcgui.Window(10000)
	# WIN.clearProperty('rbt.script_started')
	# if not WIN.getProperty('rbt.script_started'):
	xbmc.log(msg='Retro BIOS Tool:  Tool Started', level=xbmc.LOGINFO)
	# WIN.setProperty('rbt.script_started','True')
	addon_name = 'plugin.program.retrobiostool'
	addon_handle = xbmcaddon.Addon(id='%(addon_name)s' % {'addon_name':addon_name})
	bios_folder = addon_handle.getSetting(id='rbt_folder')
	if addon_handle.getSetting(id='rbt_generate_report') == 'true':
		generate_report = True
	else:
		generate_report = False
	addon_timeout = 5
	bios_keyword = ['firmware%(number)s_path'%{'number':x} for x in range(0,21)]
	libretro_git = r'https://raw.githubusercontent.com/libretro/libretro-super/master/dist/info/xxx_core_xxx.info'
	#These games are already known to not require any system/bios files, so skip them to make the tool faster
	ignore_these_addons = ['game.libretro',
							 'game.libretro.2048',
							 'game.libretro.2048_libretro_buildbot',
							 'game.libretro.81',
							 'game.libretro.81_libretro_buildbot',
							 'game.libretro.beetle-bsnes',
							 'game.libretro.beetle-bsnes_libretro_buildbot',
							 'game.libretro.beetle-bsnes_cplusplus98',
							 'game.libretro.beetle-bsnes_cplusplus98_libretro_buildbot',
							 'game.libretro.beetle-ngp',
							 'game.libretro.beetle-ngp_libretro_buildbot',
							 'game.libretro.beetle-vb',
							 'game.libretro.beetle-vb_libretro_buildbot',
							 'game.libretro.beetle-wswan',
							 'game.libretro.beetle-wswan_libretro_buildbot',
							 'game.libretro.bnes',
							 'game.libretro.bnes_libretro_buildbot',
							 'game.libretro.cannonball',
							 'game.libretro.cannonball_libretro_buildbot',
							 'game.libretro.cap32',
							 'game.libretro.cap32_libretro_buildbot',
							 'game.libretro.chailove',
							 'game.libretro.chailove_libretro_buildbot',
							 'game.libretro.craft',
							 'game.libretro.craft_libretro_buildbot',
							 'game.libretro.crocods',
							 'game.libretro.crocods_libretro_buildbot',
							 'game.libretro.daphne',
							 'game.libretro.daphne_libretro_buildbot',
							 'game.libretro.dinothawr',
							 'game.libretro.dinothawr_libretro_buildbot',
							 'game.libretro.dosbox',
							 'game.libretro.dosbox_libretro_buildbot',
							 'game.libretro.dosbox_svn',
							 'game.libretro.dosbox_svn_libretro_buildbot',
							 'game.libretro.easyrpg',
							 'game.libretro.easyrpg_libretro_buildbot',
							 'game.libretro.emux_nes',
							 'game.libretro.emux_nes_libretro_buildbot',
							 'game.libretro.fbalpha',
							 'game.libretro.fbalpha2012',
							 'game.libretro.fbalpha2012_libretro_buildbot',
							 'game.libretro.fbalpha2012_cps1',
							 'game.libretro.fbalpha2012_cps1_libretro_buildbot',
							 'game.libretro.fbalpha2012_cps2',
							 'game.libretro.fbalpha2012_cps2_libretro_buildbot',
							 'game.libretro.fbalpha2012_neogeo',
							 'game.libretro.fbalpha2012_neogeo_libretro_buildbot',
							 'game.libretro.fbalpha_libretro_buildbot',
							 'game.libretro.fuse',
							 'game.libretro.fuse_libretro_buildbot',
							 'game.libretro.gearboy',
							 'game.libretro.gearboy_libretro_buildbot',
							 'game.libretro.gearsystem',
							 'game.libretro.gearsystem_libretro_buildbot',
							 'game.libretro.gme',
							 'game.libretro.gme_libretro_buildbot',
							 'game.libretro.gw',
							 'game.libretro.gw_libretro_buildbot',
							 'game.libretro.lutro',
							 'game.libretro.lutro_libretro_buildbot',
							 'game.libretro.mednafen_ngp',
							 'game.libretro.mednafen_ngp_libretro_buildbot',
							 'game.libretro.mednafen_snes',
							 'game.libretro.mednafen_snes_libretro_buildbot',
							 'game.libretro.mednafen_vb',
							 'game.libretro.mednafen_vb_libretro_buildbot',
							 'game.libretro.mednafen_wswan',
							 'game.libretro.mednafen_wswan_libretro_buildbot',
							 'game.libretro.meteor',
							 'game.libretro.meteor_libretro_buildbot',
							 'game.libretro.mrboom',
							 'game.libretro.mrboom_libretro_buildbot',
							 'game.libretro.nekop2',
							 'game.libretro.nekop2_libretro_buildbot',
							 'game.libretro.nx',
							 'game.libretro.nx_libretro_buildbot',
							 'game.libretro.nxengine',
							 'game.libretro.nxengine_libretro_buildbot',
							 'game.libretro.openlara',
							 'game.libretro.openlara_libretro_buildbot',
							 'game.libretro.pocketcdg',
							 'game.libretro.pocketcdg_libretro_buildbot',
							 'game.libretro.prboom',
							 'game.libretro.prboom_libretro_buildbot',
							 'game.libretro.quicknes',
							 'game.libretro.quicknes_libretro_buildbot',
							 'game.libretro.reminiscence',
							 'game.libretro.reminiscence_libretro_buildbot',
							 'game.libretro.scummvm',
							 'game.libretro.scummvm_libretro_buildbot',
							 'game.libretro.snes9x2002',
							 'game.libretro.snes9x2002_libretro_buildbot',
							 'game.libretro.snes9x2005',
							 'game.libretro.snes9x2005_libretro_buildbot',
							 'game.libretro.snes9x2005_plus',
							 'game.libretro.snes9x2005_plus_libretro_buildbot',
							 'game.libretro.snes9x2010',
							 'game.libretro.snes9x2010_libretro_buildbot',
							 'game.libretro.stella',
							 'game.libretro.stella2014',
							 'game.libretro.stella2014_libretro_buildbot',
							 'game.libretro.stella_libretro_buildbot',
							 'game.libretro.tgbdual',
							 'game.libretro.tgbdual_libretro_buildbot',
							 'game.libretro.theodore',
							 'game.libretro.theodore_libretro_buildbot',
							 'game.libretro.thepowdertoy',
							 'game.libretro.thepowdertoy_libretro_buildbot',
							 'game.libretro.tyrquake',
							 'game.libretro.tyrquake_libretro_buildbot',
							 'game.libretro.vecx',
							 'game.libretro.vecx_libretro_buildbot',
							 'game.libretro.vice_x128',
							 'game.libretro.vice_x128_libretro_buildbot',
							 'game.libretro.vice_x64',
							 'game.libretro.vice_x64_libretro_buildbot',
							 'game.libretro.vice_x64sc',
							 'game.libretro.vice_x64sc_libretro_buildbot',
							 'game.libretro.vice_xplus4',
							 'game.libretro.vice_xplus4_libretro_buildbot',
							 'game.libretro.vice_xvic',
							 'game.libretro.vice_xvic_libretro_buildbot',
							 'game.libretro.virtualjaguar',
							 'game.libretro.virtualjaguar_libretro_buildbot',
							 'game.libretro.xrick',
							 'game.libretro.xrick_libretro_buildbot']

	#Rename the following addons to match libretro naming
	retroplayer_to_libretro_map = {'bsnes-mercury-accuracy':'bsnes_mercury_accuracy',
	'bsnes-mercury-balanced':'bsnes_mercury_balanced',
	'bsnes-mercury-performance':'bsnes_mercury_performance',
	'genplus':'genesis_plus_gx',
	'beetle-gba':'mednafen_gba',
	'beetle-lynx':'mednafen_lynx',
	'beetle-ngp':'mednafen_ngp',
	'beetle-pce-fast':'mednafen_pce_fast',
	'beetle-pcfx':'mednafen_pcfx',
	'beetle-psx':'mednafen_psx',
	'beetle-saturn':'mednafen_saturn',
	'beetle-bsnes':'mednafen_snes',
	'beetle-supergrafx':'mednafen_supergrafx',
	'beetle-vb':'mednafen_vb',
	'beetle-wswan':'mednafen_wswan',
	'pcsx-rearmed':'pcsx_rearmed',
	'uae':'puae',
	'vba-next':'vba_next',
	'vice':'vice_x64'}

	#These special cases have folders listed in their info files rather than all the individual files, need to copy the entire folder
	special_folder_cases_map ={'game.libretro.bluemsx':['Databases','Machines'],
	'game.libretro.bluemsx_libretro_buildbot':['Databases','Machines'],
	'game.libretro.reicast':['dc'],
	'game.libretro.dolphin_libretro_buildbot':['dolphin-emu'],
	'game.libretro.dolphin':['dolphin-emu'],
	'game.libretro.mame':['mame'],
	'game.libretro.mame_libretro_buildbot':['mame'],
	'game.libretro.mame2000':['mame2000'],
	'game.libretro.mame2000_libretro_buildbot':['mame2000'],
	'game.libretro.mame2003':['mame2003'],
	'game.libretro.mame2003_libretro_buildbot':['mame2003'],
	'game.libretro.mame2003_plus':['mame2003-plus'],
	'game.libretro.mame2003_plus_libretro_buildbot':['mame2003-plus'],
	'game.libretro.mame2010':['mame2010'],
	'game.libretro.mame2010_libretro_buildbot':['mame2010'],
	'game.libretro.mame2014':['mame2014'],
	'game.libretro.mame2014_libretro_buildbot':['mame2014'],
	'game.libretro.mame2015':['mame2015'],
	'game.libretro.mame2015_libretro_buildbot':['mame2015'],
	'game.libretro.mess2015':['mess2015'],
	'game.libretro.mess2015_libretro_buildbot':['mess2015'],
	'game.libretro.ppsspp':['PPSSPP'],
	'game.libretro.ppsspp_libretro_buildbot':['PPSSPP'],
	'game.libretro.puae':['uae_data'],
	'game.libretro.puae_libretro_buildbot':['uae_data'],
	'game.libretro.ume2014':['ume2014'],
	'game.libretro.ume2014_libretro_buildbot':['ume2014'],
	}

	#Initialize report dict
	report_data = dict()
	report_data['addon_id'] = list()
	report_data['firmware_listed'] = list()
	report_data['firmware_files'] = list()
	report_data['firmware_found'] = list()
	report_data['info_file'] = list()

	if bios_folder is None or len(bios_folder)<1:
		current_dialog = xbmcgui.Dialog()
		ret = current_dialog.ok('Retro BIOS Tool','The tool did not run.[CR]Enter a BIOS file location in settings first!')
	else:
		try:
			addons_available = xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "method": "Addons.GetAddons","params":{"type":"kodi.gameclient", "enabled": true}, "id": "1"}')
			addon_ids = [x.get('addonid') for x in json.loads(addons_available).get('result').get('addons') if x.get('type') == 'kodi.gameclient' and x.get('addonid') not in ignore_these_addons]
			xbmc.log(msg='Retro BIOS Tool:  The following addons will be checked %(current_aids)s' % {'current_aids':', '.join(addon_ids)}, level=xbmc.LOGDEBUG)
		except:
			addon_ids = None
		if addon_ids is not None:
			total_files_copied = 0
			dp = xbmcgui.DialogProgress()
			dp.create('Retro BIOS Tools','Checking for BIOS Files')
			dp.update(0)
			s = requests.Session()
			for iiaid,aid in enumerate(addon_ids):
				dp.update(int(100*(iiaid+1)/len(addon_ids)))
				xbmc.log(msg='Retro BIOS Tool: Checking addon %(current_aid)s' % {'current_aid':aid}, level=xbmc.LOGINFO)
				report_data['addon_id'].append(aid)
				report_data['firmware_listed'].append(False)
				report_data['firmware_files'].append(None)
				report_data['firmware_found'].append(None)
				report_data['info_file'].append('')
				if dp.iscanceled():
					run_was_cancelled = True
					dp.close()
					raise
				if aid.replace('game.libretro.','').replace('_libretro_buildbot','') in retroplayer_to_libretro_map.keys():
					current_git_url = libretro_git.replace('xxx_core_xxx',retroplayer_to_libretro_map[aid.replace('game.libretro.','').replace('_libretro_buildbot','')]+'_libretro')
				else:
					current_git_url = libretro_git.replace('xxx_core_xxx',aid.replace('game.libretro.','').replace('_libretro_buildbot','')+'_libretro')
				xbmc.log(msg='Retro BIOS Tool:  Checking libretro for core info at %(current_git_url)s' % {'current_git_url':current_git_url}, level=xbmc.LOGDEBUG)
				try:
					r = s.get(current_git_url,verify=False,stream=True,timeout=addon_timeout)
				except Exception as current_exc:
					xbmc.log(msg='Retro BIOS Tool:  Error getting libretro for core info at %(current_exc)s' % {'current_exc':current_exc}, level=xbmc.LOGDEBUG)
				current_info = r.text
				if len(current_info)>0:
					report_data['info_file'][-1] = current_info
				current_bios_files = list()
				for bk in bios_keyword:
					current_check = re.findall(r'%(current_bk)s\s+=\s+\"(.*?)\"'%{'current_bk':bk},current_info)
					if current_check is not None and len(current_check)>0:
						current_bios_files.append(current_check[0].strip())
				if len(current_bios_files)>0:
					report_data['firmware_listed'][-1] = True
					if type(current_bios_files) is list:
						report_data['firmware_files'][-1] = current_bios_files
						report_data['firmware_found'][-1] = [False for x in current_bios_files]
					else:
						report_data['firmware_files'][-1] = [current_bios_files]
						report_data['firmware_found'][-1] = [False]
					xbmc.log(msg='Retro BIOS Tool:  Looking for the following bios files %(current_files)s' % {'current_files':', '.join(current_bios_files)}, level=xbmc.LOGDEBUG)
					current_addon = xbmcaddon.Addon(id='%(addon_name)s' % {'addon_name':aid})
					current_addon_data_folder = py2_decode(xbmc.translatePath(current_addon.getAddonInfo('profile')))
					current_addon_resources_folder = os.path.join(current_addon_data_folder,'resources')
					current_addon_systems_folder = os.path.join(current_addon_resources_folder,'system')
					for cbf in current_bios_files:
						current_bios_fullpath = os.path.join(bios_folder,*os.path.split(cbf))
						if xbmcvfs.exists(current_bios_fullpath):
							xbmc.log(msg='Retro BIOS Tool: Found file %(current_cbf)s' % {'current_cbf':cbf}, level=xbmc.LOGDEBUG)
							if not xbmcvfs.exists(os.path.join(current_addon_data_folder,'')):
								xbmc.log(msg='Retro BIOS Tool:  The folder %(current_folder)s does not yet exist, so it will be created' % {'current_folder':current_addon_data_folder}, level=xbmc.LOGDEBUG)
								if not xbmcvfs.mkdir(os.path.join(current_addon_data_folder,'')):
									xbmc.log(msg='Retro BIOS Tool:  Unable to create addon_data folder', level=xbmc.LOGERROR)
							if not xbmcvfs.exists(os.path.join(current_addon_resources_folder,'')):
								xbmc.log(msg='Retro BIOS Tool:  The folder %(current_folder)s does not yet exist, so it will be created' % {'current_folder':current_addon_resources_folder}, level=xbmc.LOGDEBUG)
								if not xbmcvfs.mkdir(os.path.join(current_addon_resources_folder,'')):
									xbmc.log(msg='Retro BIOS Tool:  Unable to create addon_data resources folder', level=xbmc.LOGERROR)
							if not xbmcvfs.exists(os.path.join(current_addon_systems_folder,'')):
								xbmc.log(msg='Retro BIOS Tool:  The folder %(current_folder)s does not yet exist, so it will be created' % {'current_folder':current_addon_systems_folder}, level=xbmc.LOGDEBUG)
								if not xbmcvfs.mkdir(os.path.join(current_addon_systems_folder,'')):
									xbmc.log(msg='Retro BIOS Tool:  Unable to create addon_data resources/system folder', level=xbmc.LOGERROR)
							if not xbmcvfs.exists(os.path.join(current_addon_systems_folder,cbf)):
								if xbmcvfs.copy(os.path.join(bios_folder,cbf),os.path.join(current_addon_systems_folder,cbf)): #Copy the file to the correct system folder
									xbmc.log(msg='Retro BIOS Tool: Copying file %(current_cbf)s to %(current_folder)s' % {'current_cbf':os.path.join(bios_folder,cbf),'current_folder':os.path.join(current_addon_systems_folder,cbf)}, level=xbmc.LOGINFO)
									total_files_copied = total_files_copied+1
									report_data['firmware_found'][-1][report_data['firmware_files'][-1].index(cbf)] = True
								else:
									xbmc.log(msg='Retro BIOS Tool: Error copying file %(current_cbf)s to %(current_folder)s' % {'current_cbf':os.path.join(bios_folder,cbf),'current_folder':os.path.join(current_addon_systems_folder,cbf)}, level=xbmc.LOGERROR)
							else:
								xbmc.log(msg='Retro BIOS Tool: BIOS file %(current_cbf)s already present in %(current_folder)s' % {'current_cbf':cbf,'current_folder':os.path.join(current_addon_systems_folder,cbf)}, level=xbmc.LOGDEBUG)
								report_data['firmware_found'][-1][report_data['firmware_files'][-1].index(cbf)] = True
						else:
							if xbmcvfs.exists(os.path.join(current_addon_systems_folder,cbf)):
								report_data['firmware_found'][-1][report_data['firmware_files'][-1].index(cbf)] = True
							else:
								report_data['firmware_found'][-1][report_data['firmware_files'][-1].index(cbf)] = False
							xbmc.log(msg='Retro BIOS Tool: Unable to find the file in your BIOS folder %(current_cbf)s ' % {'current_cbf':os.path.join(bios_folder,cbf)}, level=xbmc.LOGERROR)
				else:
					xbmc.log(msg='Retro BIOS Tool: No bios files found for %(current_aid)s' % {'current_aid':aid}, level=xbmc.LOGDEBUG)
					report_data['firmware_listed'][-1] = False
				#Check folder specific cases
				if aid in special_folder_cases_map.keys():
					current_addon = xbmcaddon.Addon(id='%(addon_name)s' % {'addon_name':aid})
					current_addon_data_folder = py2_decode(xbmc.translatePath(current_addon.getAddonInfo('profile')))
					current_addon_resources_folder = os.path.join(current_addon_data_folder,'resources')
					current_addon_systems_folder = os.path.join(current_addon_resources_folder,'system')
					current_bios_folder_fullpaths = [os.path.join(bios_folder,x) for x in special_folder_cases_map[aid]]
					current_ind_folders = [x for x in special_folder_cases_map[aid]]
					for cbfi,current_bios_folder_fullpath in enumerate(current_bios_folder_fullpaths):
						report_data['firmware_listed'][-1] = True
						report_data['firmware_files'][-1] = [', '.join([x+' (Folder)' for x in special_folder_cases_map[aid]])]
						report_data['firmware_found'][-1] = [False]
						xbmc.log(msg='Retro BIOS Tool:  Looking for the following bios folder %(current_folder)s' % {'current_folder':current_ind_folders[cbfi]}, level=xbmc.LOGDEBUG)
						if xbmcvfs.exists(os.path.join(current_bios_folder_fullpath,'')):
							if not xbmcvfs.exists(os.path.join(current_addon_data_folder,'')):
								xbmc.log(msg='Retro BIOS Tool:  The folder %(current_folder)s does not yet exist, so it will be created' % {'current_folder':current_addon_data_folder}, level=xbmc.LOGDEBUG)
								if not xbmcvfs.mkdir(os.path.join(current_addon_data_folder,'')):
									xbmc.log(msg='Retro BIOS Tool:  Unable to create addon_data folder', level=xbmc.LOGERROR)
							if not xbmcvfs.exists(os.path.join(current_addon_resources_folder,'')):
								xbmc.log(msg='Retro BIOS Tool:  The folder %(current_folder)s does not yet exist, so it will be created' % {'current_folder':current_addon_resources_folder}, level=xbmc.LOGDEBUG)
								if not xbmcvfs.mkdir(os.path.join(current_addon_resources_folder,'')):
									xbmc.log(msg='Retro BIOS Tool:  Unable to create addon_data resources folder', level=xbmc.LOGERROR)
							if not xbmcvfs.exists(os.path.join(current_addon_systems_folder,'')):
								xbmc.log(msg='Retro BIOS Tool:  The folder %(current_folder)s does not yet exist, so it will be created' % {'current_folder':current_addon_systems_folder}, level=xbmc.LOGDEBUG)
								if not xbmcvfs.mkdir(os.path.join(current_addon_systems_folder,'')):
									xbmc.log(msg='Retro BIOS Tool:  Unable to create addon_data resources/system folder', level=xbmc.LOGERROR)
							if not xbmcvfs.exists(os.path.join(current_addon_systems_folder,current_ind_folders[cbfi],'')):
								copied_folder_files, folder_copy_success = copy_directory_contents_xbmcvfs(current_bios_folder_fullpath,os.path.join(current_addon_systems_folder,current_ind_folders[cbfi]))
								if folder_copy_success:
									xbmc.log(msg='Retro BIOS Tool: Successfully copied the BIOS folder %(current_folder)s ' % {'current_folder':os.path.join(bios_folder,current_ind_folders[cbfi])}, level=xbmc.LOGDEBUG)
									report_data['firmware_found'][-1] = [True]
									total_files_copied = total_files_copied+1
								else:
									xbmc.log(msg='Retro BIOS Tool: The BIOS folder %(current_folder)s was found but could not be copied' % {'current_folder':os.path.join(bios_folder,current_ind_folders[cbfi])}, level=xbmc.LOGERROR)
									report_data['firmware_found'][-1] = [False]
							else:
								xbmc.log(msg='Retro BIOS Tool: The BIOS folder %(current_folder)s is already present' % {'current_folder':os.path.join(current_addon_systems_folder,current_ind_folders[cbfi])}, level=xbmc.LOGDEBUG)
								report_data['firmware_found'][-1] = [True]

						else:
							if xbmcvfs.exists(os.path.join(current_addon_systems_folder,current_ind_folders[cbfi],'')):
								report_data['firmware_found'][-1] = [True]
								xbmc.log(msg='Retro BIOS Tool: The BIOS folder is already present in your addon folder %(current_folder)s ' % {'current_folder':os.path.join(current_addon_systems_folder,current_ind_folders[cbfi])}, level=xbmc.LOGDEBUG)
							else:
								report_data['firmware_found'][-1] = [False]
								xbmc.log(msg='Retro BIOS Tool: Unable to find the folder in your BIOS folder %(current_folder)s ' % {'current_folder':os.path.join(current_addon_systems_folder,current_ind_folders[cbfi])}, level=xbmc.LOGDEBUG)
			dp.close()
			current_dialog = xbmcgui.Dialog()
			if total_files_copied >0:
				ok_ret = current_dialog.ok('Completed','Tool copied %(total_files_copied)s total files.'% {'total_files_copied': total_files_copied})
			else:
				ok_ret = current_dialog.ok('Completed','Tool did not copy any files'% {'total_files_copied': total_files_copied})
	if generate_report:
		xbmc.log(msg='Retro BIOS Tool:  Report Generated', level=xbmc.LOGDEBUG)
		xbmcplugin.addDirectoryItem(plugin_handle.handle,'',xbmcgui.ListItem('Retro BIOS Tool Report ([COLOR green]green=present[/COLOR], [COLOR red]red=missing[/COLOR]): ', offscreen=True))
		for iiaid,aid in enumerate(report_data['addon_id']):
			report_item = 'Addon: %(current_addon_id)s, BIOS Listed: %(current_firmware_listed)s, ' % {'current_addon_id':aid, 'current_firmware_listed':report_data['firmware_listed'][iiaid]}
			if report_data['firmware_listed'][iiaid]:
				report_subitem = 'Files: '
				for icff, cff in enumerate(report_data['firmware_files'][iiaid]):
					if report_data['firmware_found'][iiaid][icff]:
						report_subitem = report_subitem+'[COLOR green]%(current_ff)s[/COLOR], '% {'current_ff':cff}
					else:
						report_subitem = report_subitem+'[COLOR red]%(current_ff)s[/COLOR], '% {'current_ff':cff}
				report_item = report_item+report_subitem
			if report_item.endswith(', '):
				report_item = report_item[:-2]
			li = xbmcgui.ListItem(report_item, offscreen=True)
			li.setInfo('video', {'plot': report_subitem+'[CR]'+report_data['info_file'][iiaid]})
			if xbmcvfs.exists(xbmc.translatePath(os.path.join('special://home','addons',str(aid),'icon.png'))):
				li.setArt({ 'icon': xbmc.translatePath(os.path.join('special://home','addons',str(aid),'icon.png'))})
			elif xbmcvfs.exists(xbmc.translatePath(os.path.join('special://home','addons',str(aid),'resources','icon.png'))):
				li.setArt({ 'icon': xbmc.translatePath(os.path.join('special://home','addons',str(aid),'resources','icon.png'))})
			elif xbmcvfs.exists(xbmc.translatePath(os.path.join('special://home','addons',str(aid),'icon.jpg'))):
				li.setArt({ 'icon': xbmc.translatePath(os.path.join('special://home','addons',str(aid),'icon.jpg'))})
			elif xbmcvfs.exists(xbmc.translatePath(os.path.join('special://home','addons',str(aid),'resources','icon.jpg'))):
				li.setArt({ 'icon': xbmc.translatePath(os.path.join('special://home','addons',str(aid),'resources','icon.jpg'))})
			else:
				xbmc.log(msg='Retro BIOS Tool: No icon found for %(current_aid)s' % {'current_aid':aid}, level=xbmc.LOGDEBUG)
			xbmcplugin.addDirectoryItem(plugin_handle.handle,'',li)
		xbmcplugin.endOfDirectory(plugin_handle.handle)
	else:
		xbmc.log(msg='Retro BIOS Tool:  Report Skipped', level=xbmc.LOGDEBUG)
	# WIN.clearProperty('rbt.script_started')
	xbmc.log(msg='Retro BIOS Tool:  Tool completed', level=xbmc.LOGINFO)
	# else:
	# 	xbmc.log(msg='Retro BIOS Tool:  Tool already running', level=xbmc.LOGINFO)

if __name__ == '__main__':
	plugin_handle.run(sys.argv)