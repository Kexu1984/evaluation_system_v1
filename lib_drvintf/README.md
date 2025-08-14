This is a c driver test code. 

We create an c driver: 
1. Convert the dma operation process described in: test_model.py::test_dma_mem2mem into corresponding c logic(main.c::test_dma_mem2mem)
2. execute "python test_comm_model.py" in one terminal(Linux env with python3+)
3. execute "./icd3_simulator" in another terminal
Then we can see the dma model be triggered to start memory copy.


The basic framework needed in main.c can show the repo: https://github.com/CjieSun/NewICD3.git
