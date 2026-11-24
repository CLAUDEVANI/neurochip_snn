`timescale 1ns / 1ps

module snn_layer #(
    parameter WIDTH = 8,
    parameter V_TH  = 100
)(
    input  wire       clk,
    input  wire       rst_n,
    input  wire       en,
    input  wire [1:0] spikes_in,
    output wire [3:0] spikes_out
);

    genvar n;
    generate
        for (n = 0; n < 4; n = n + 1) begin : gen_neuron
            wire [WIDTH-1:0] syn_out_0;
            wire [WIDTH-1:0] syn_out_1;
            wire [WIDTH:0]   syn_sum_ext;
            wire [WIDTH-1:0] syn_sum_sat;
            wire [WIDTH-1:0] v_mem_unused;
            wire [WIDTH-1:0] w0_unused, w1_unused;

            // Sinapse 0 do neurônio n
            stdp_synapse #(
                .WIDTH(WIDTH),
                .INIT_W(30 + n * 5)
            ) u_syn0 (
                .clk(clk),
                .rst_n(rst_n),
                .en(en),
                .pre_spike(spikes_in[0]),
                .post_spike(spikes_out[n]),
                .weight(w0_unused),
                .syn_out(syn_out_0)
            );

            // Sinapse 1 do neurônio n
            stdp_synapse #(
                .WIDTH(WIDTH),
                .INIT_W(45 - n * 5)
            ) u_syn1 (
                .clk(clk),
                .rst_n(rst_n),
                .en(en),
                .pre_spike(spikes_in[1]),
                .post_spike(spikes_out[n]),
                .weight(w1_unused),
                .syn_out(syn_out_1)
            );

            // Soma saturada em 8 bits (evita overflow)
            assign syn_sum_ext = syn_out_0 + syn_out_1;
            assign syn_sum_sat = syn_sum_ext[WIDTH] ? {WIDTH{1'b1}} : syn_sum_ext[WIDTH-1:0];

            // Neurônio LIF
            lif_neuron #(
                .WIDTH(WIDTH),
                .V_TH(V_TH),
                .LEAK_SHIFT(3)
            ) u_lif (
                .clk(clk),
                .rst_n(rst_n),
                .en(en),
                .syn_in(syn_sum_sat),
                .spike_out(spikes_out[n]),
                .v_mem(v_mem_unused)
            );
        end
    endgenerate

endmodule