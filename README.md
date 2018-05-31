# SDN-ECMP

##authors
Yehonatan Simhon : 30150645
Shai Hood : 304800402
Mark Rabayev : 310356621
Carin Krechmer : 206013856

### running the program
in order to run the program follow the next steps:

### 1
copy the all the .py files into the pox library
### 2
in the pox library open terminal and run : python topo.py
after this command 3 new .json files will appear in the pox folder
### 3
in same terminal run : ./pox.py controller
### 4
open a new terminal and run : sudo python TopologyBuilder.py
### test the program
run in mininet 'iperf'
or try pingall

### exiting
type 'exit' in mininet
combo ctrl+c in the controller