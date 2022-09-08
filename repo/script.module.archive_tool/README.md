
archive_tool is a set of common python functions to work with the Kodi archive virtual file system (vfs) binary addons such as [vfs.libarchive](https://github.com/xbmc/vfs.libarchive) and [vfs.rar](https://github.com/xbmc/vfs.rar)

Simplest usage example:
```
import archive_tool

my_archive = archive_tool.archive_tool(archive_file = 'myfile.zip',directory_out = '/my/output_directory/') #Current archive object using vfs.libarchive

file_listing = my_archive.list_all() #Lists all files in the archive

file_listing = my_archive.stat_all() #Dict of all files in the archive containing fullpath, filename, file size (extracted)

files_extracted, success_of_extraction = my_archive.extract()  #Extracts all files to directory_out, returns list of files extracted and True/False for extraction success.  Defaults to extract all files in the archive.
```
or
```
files_extracted, success_of_extraction = my_archive.extract(files_to_extract=file_listing[0])  #Extracts only the listed file(s) in the archive to directory_out, returns list of files extracted and True/False for extraction success
```
Additional functions:
```
my_archive = archive_tool.archive_tool(archive_file = 'myfile.zip',directory_out = '/my/output_directory/', flatten_archive=True) #Flatten files when copying from archive, removing folder structure (default is False)

my_archive.archive_file('myfile2.zip') #Updates the currently set archive

my_archive.directory_out('/my/output_directory2/') #Updates the currently set output directory

my_archive.files_to_extract([file_listing[0],file_listing[3]]) #Updates the currently set file(s) to extract from the archive

my_archive = archive_tool.archive_tool(archive_file = 'myfile.zip',directory_out = '/my/output_directory/', show_progress=True) #Includes a background notification on current extraction progress of the archive
```

Use of vfs.rar (Kodi v19 or greater):

Almost all archives can be handled by vfs.libarchive.  The only exception found at this point are RAR archives which are automatically handled by vfs.rar

To test archive types, there is a test script for this module which can be run from the addon settings.
![](https://i.imgur.com/VMEnjXU.png)