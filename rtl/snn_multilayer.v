`timescale 1ns / 1ps

module snn_multilayer #(
    parameter WIDTH = 8,
    parameter V_TH  = 100
)(
    input  wire       clk,
    input  wire       rst_n,
    input  wire       en,
    input  wire [1:0] spikes_in,
    output wire [3:0] hidden_spikes,
    output wire [3:0] spikes_out
);

    wire [1:0] l2_in;

    // Camada 1 (Oculta): 2 entradas -> 4 neurônios LIF + 8 sinapses STDP
    snn_layer #(
        .WIDTH(WIDTH),
        .V_TH(V_TH)
    ) u_layer1 (
        .clk(clk),
        .rst_n(rst_n),
        .en(en),
        .spikes_in(spikes_in),
        .spikes_out(hidden_spikes)
    );

    // Pooling de eventos (agrupa pares de neurônios da Camada 1 para a Camada 2)
    assign l2_in[0] = hidden_spikes[0] | hidden_spikes[1];
    assign l2_in[1] = hidden_spikes[2] | hidden_spikes[3];

    // Camada 2 (Saída): 2 entradas agrupadas -> 4 neurônios LIF + 8 sinapses STDP
    snn_layer #(
        .WIDTH(WIDTH),
        .V_TH(V_TH)
    ) u_layer2 (
        .clk(clk),
        .rst_n(rst_n),
        .en(en),
        .spikes_in(l2_in),
        .spikes_out(spikes_out)
    );

endmodule