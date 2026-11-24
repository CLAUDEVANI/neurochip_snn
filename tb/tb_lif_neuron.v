`timescale 1ns / 1ps

module tb_lif_neuron;

    reg        clk;
    reg        rst_n;
    reg        en;
    reg  [7:0] syn_in;
    wire       spike_out;
    wire [7:0] v_mem;

    lif_neuron #(
        .WIDTH(8),
        .V_TH(100),
        .LEAK_SHIFT(3)
    ) dut (
        .clk(clk),
        .rst_n(rst_n),
        .en(en),
        .syn_in(syn_in),
        .spike_out(spike_out),
        .v_mem(v_mem)
    );

    always #5 clk = ~clk;

    initial begin
        $dumpfile("build/lif_neuron.vcd");
        $dumpvars(0, tb_lif_neuron);

        clk    = 0;
        rst_n  = 0;
        en     = 0;
        syn_in = 0;

        #20 rst_n = 1;
        en = 1;

        repeat (12) begin
            @(posedge clk);
            syn_in = 8'd35;
        end

        repeat (10) begin
            @(posedge clk);
            syn_in = 8'd0;
        end

        $finish;
    end

    initial begin
        $monitor("t=%0t | syn_in=%3d | v_mem=%3d | spike_out=%b",
                 $time, syn_in, v_mem, spike_out);
    end

endmodule