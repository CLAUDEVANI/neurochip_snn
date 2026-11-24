`timescale 1ns / 1ps

module tb_aer_top;

    reg        clk;
    reg        rst_n;
    reg        en;
    reg        aer_in_valid;
    reg        aer_in_addr;
    wire       aer_out_valid;
    wire [1:0] aer_out_addr;

    aer_top dut (
        .clk(clk),
        .rst_n(rst_n),
        .en(en),
        .aer_in_valid(aer_in_valid),
        .aer_in_addr(aer_in_addr),
        .aer_out_valid(aer_out_valid),
        .aer_out_addr(aer_out_addr)
    );

    always #5 clk = ~clk;

    integer i;
    initial begin
        $dumpfile("build/aer_top.vcd");
        $dumpvars(0, tb_aer_top);

        clk = 0; rst_n = 0; en = 0;
        aer_in_valid = 0; aer_in_addr = 0;

        #20 rst_n = 1;
        en = 1;

        // Envia 25 eventos AER alternando entre entrada 0 e entrada 1
        for (i = 0; i < 25; i = i + 1) begin
            @(posedge clk);
            aer_in_valid = 1'b1;
            aer_in_addr  = (i % 3 == 0) ? 1'b1 : 1'b0;
        end

        @(posedge clk);
        aer_in_valid = 1'b0;
        repeat (5) @(posedge clk);

        $finish;
    end

    always @(posedge clk) begin
        if (aer_out_valid)
            $display("t=%0t | SPIKE AER OUT -> Neuronio %0d disparou!", $time, aer_out_addr);
    end

endmodule