Discus is a program to display hard drive space usage, much like the
standard UN*X command df.  
                         
Discus aims to make df(1) prettier. Features include color, bar graphs, and
smart formatting of numbers (automatically choosing the most suitable size
from kilobytes, megabytes, gigabytes, or terabytes). Or choose your own
size, along with specifying the number of decimal places you'd like to see.

To configure Discus on a system-wide basis, edit the /etc/discusrc file. 
But you should probably change things just for yourself, by copying
/etc/discusrc to ~/.discusrc and editing that.

The source code is contained in the discus file itself, as it is a Python
code encapsulated in a shell script.

Yes, I chose the name Discus because of the similarity to "disk use."  And
no, I didn't misspell discuss.  A discus is a round thingie people throw.

Newest versions of Discus may be found at:
https://github.com/ncarrier/discus
