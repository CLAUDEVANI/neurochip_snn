.PHONY: py sim wave sim_top wave_top real_sim synth synth_tt synth_multi schematic dashboard clean

RTL_SRCS   = rtl/lif_neuron.v rtl/stdp_synapse.v rtl/snn_layer.v rtl/aer_top.v
TT_SRCS    = $(RTL_SRCS) rtl/tt_um_neurochip_snn.v
MULTI_SRCS = rtl/lif_neuron.v rtl/stdp_synapse.v rtl/snn_layer.v rtl/snn_multilayer.v

py:
	python3 sim/sim_snn_stdp.py

sim:
	mkdir -p build
	iverilog -o build/sim_lif rtl/lif_neuron.v tb/tb_lif_neuron.v
	vvp build/sim_lif

wave: sim
	gtkwave build/lif_neuron.vcd &

sim_top:
	mkdir -p build
	iverilog -o build/sim_aer $(RTL_SRCS) tb/tb_aer_top.v
	vvp build/sim_aer

wave_top: sim_top
	gtkwave build/aer_top.vcd &

real_sim:
	mkdir -p build
	python3 sim/encode_signal_aer.py
	iverilog -o build/sim_real $(RTL_SRCS) tb/tb_aer_real_signal.v
	vvp build/sim_real

synth:
	mkdir -p build
	yosys -p "read_verilog $(RTL_SRCS); synth -top aer_top; stat"

synth_tt:
	mkdir -p build
	yosys -p "read_verilog $(TT_SRCS); synth -top tt_um_neurochip_snn; stat"

synth_multi:
	mkdir -p build
	yosys -p "read_verilog $(MULTI_SRCS); synth -top snn_multilayer; stat"

schematic:
	mkdir -p build
	yosys -p "read_verilog rtl/lif_neuron.v; proc; opt; show -format svg -prefix build/lif_neuron_schematic lif_neuron"
	yosys -p "read_verilog $(RTL_SRCS); proc; opt; show -format svg -prefix build/aer_top_schematic aer_top"

dashboard:
	streamlit run sim/dashboard_snn.py

clean:
	rm -rf build/*

sim_multi:
	mkdir -p build
	iverilog -o build/sim_multi $(MULTI_SRCS) tb/tb_snn_multilayer.v
	vvp build/sim_multi