`timescale 1ns / 1ps

module lif_neuron #(
    parameter WIDTH      = 8,
    parameter V_TH       = 100,
    parameter LEAK_SHIFT = 3
)(
    input  wire             clk,
    input  wire             rst_n,
    input  wire             en,
    input  wire [WIDTH-1:0] syn_in,
    output reg              spike_out,
    output reg  [WIDTH-1:0] v_mem
);

    wire [WIDTH-1:0] leak;
    wire [WIDTH:0]   v_next;

    assign leak   = v_mem >> LEAK_SHIFT;
    assign v_next = (v_mem - leak) + syn_in;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            v_mem     <= {WIDTH{1'b0}};
            spike_out <= 1'b0;
        end else if (en) begin
            if (v_next >= V_TH) begin
                spike_out <= 1'b1;
                v_mem     <= {WIDTH{1'b0}};
            end else begin
                spike_out <= 1'b0;
                v_mem     <= v_next[WIDTH-1:0];
            end
        end else begin
            spike_out <= 1'b0;
        end
    end

endmodule