`timescale 1ns / 1ps

module tb_corner_cases;

    reg clk;
    reg rst_n;
    reg en;

    // --- Sinais LIF ---
    reg  [7:0] lif_syn_in;
    wire       lif_spike;
    wire [7:0] lif_vmem;

    lif_neuron #(
        .WIDTH(8),
        .V_TH(100),
        .LEAK_SHIFT(3)
    ) u_lif (
        .clk(clk),
        .rst_n(rst_n),
        .en(en),
        .syn_in(lif_syn_in),
        .spike_out(lif_spike),
        .v_mem(lif_vmem)
    );

    // --- Sinais STDP ---
    reg        stdp_pre;
    reg        stdp_post;
    wire [7:0] stdp_w;
    wire [7:0] stdp_out;

    stdp_synapse #(
        .WIDTH(8),
        .INIT_W(35),
        .MAX_W(127),
        .WINDOW(5),
        .LTP(3),
        .LTD(2)
    ) u_stdp (
        .clk(clk),
        .rst_n(rst_n),
        .en(en),
        .pre_spike(stdp_pre),
        .post_spike(stdp_post),
        .weight(stdp_w),
        .syn_out(stdp_out)
    );

    // --- Sinais Multilayer ---
    reg  [1:0] ml_in;
    wire [3:0] ml_hidden;
    wire [3:0] ml_out;

    snn_multilayer #(
        .WIDTH(8),
        .V_TH(100)
    ) u_ml (
        .clk(clk),
        .rst_n(rst_n),
        .en(en),
        .spikes_in(ml_in),
        .hidden_spikes(ml_hidden),
        .spikes_out(ml_out)
    );

    // Clock 100 MHz (10ns)
    initial clk = 0;
    always #5 clk = ~clk;

    integer i;
    integer l1_count;
    integer l2_count;
    reg [7:0] saved_vmem;

    initial begin
        rst_n      = 0;
        en         = 0;
        lif_syn_in = 0;
        stdp_pre   = 0;
        stdp_post  = 0;
        ml_in      = 2'b00;
        l1_count   = 0;
        l2_count   = 0;

        // 1. Teste de Reset Inicial
        #12;
        if (lif_vmem !== 8'd0 || lif_spike !== 1'b0) begin
            $display("ERRO: LIF nao zerou no reset!");
            $fatal(1);
        end
        if (stdp_w !== 8'd35) begin
            $display("ERRO: STDP peso inicial incorreto (%0d != 35)", stdp_w);
            $fatal(1);
        end

        rst_n = 1;
        en    = 1;

        // 2. Teste LIF: integracao, freeze com en=0 e disparo
        @(negedge clk);
        lif_syn_in = 8'd50;
        @(posedge clk); #1;
        if (lif_vmem !== 8'd50 || lif_spike !== 1'b0) begin
            $display("ERRO: LIF integracao incorreta (v_mem=%0d, spike=%0b)", lif_vmem, lif_spike);
            $fatal(1);
        end

        // Congela com en=0
        saved_vmem = lif_vmem;
        @(negedge clk);
        en = 0;
        lif_syn_in = 8'd80;
        @(posedge clk); #1;
        if (lif_vmem !== saved_vmem) begin
            $display("ERRO: LIF alterou v_mem com en=0 (%0d != %0d)", lif_vmem, saved_vmem);
            $fatal(1);
        end

        // Reabilita e força disparo (>= V_TH=100)
        @(negedge clk);
        en = 1;
        lif_syn_in = 8'd80;
        @(posedge clk); #1;
        if (lif_spike !== 1'b1) begin
            $display("ERRO: LIF deveria disparar ao cruzar V_TH (v_mem=%0d)", lif_vmem);
            $fatal(1);
        end

        // 3. Reset assincrono no meio da operacao
        @(negedge clk);
        lif_syn_in = 8'd60;
        @(posedge clk); #1;
        rst_n = 0;
        #2;
        if (lif_vmem !== 8'd0 || lif_spike !== 1'b0) begin
            $display("ERRO: Reset assincrono no meio da operacao falhou!");
            $fatal(1);
        end
        rst_n = 1;
        lif_syn_in = 8'd0;

        // 4. Teste STDP: gating de syn_out e saturacao LTP (<= MAX_W=127)
        @(negedge clk);
        stdp_pre = 1'b0;
        #1;
        if (stdp_out !== 8'd0) begin
            $display("ERRO: syn_out deve ser 0 quando pre_spike=0");
            $fatal(1);
        end
        stdp_pre = 1'b1;
        #1;
        if (stdp_out !== stdp_w) begin
            $display("ERRO: syn_out deve refletir weight quando pre_spike=1");
            $fatal(1);
        end
        stdp_pre = 1'b0;

        // Repete padrao pre -> post (LTP) ate saturar em MAX_W=127
        for (i = 0; i < 45; i = i + 1) begin
            @(negedge clk); stdp_pre = 1; stdp_post = 0;
            @(posedge clk);
            @(negedge clk); stdp_pre = 0; stdp_post = 1;
            @(posedge clk);
            @(negedge clk); stdp_pre = 0; stdp_post = 0;
            repeat (6) @(posedge clk);
        end
        #1;
        if (stdp_w > 8'd127 || stdp_w < 8'd120) begin
            $display("ERRO: STDP LTP fora da saturacao esperada (weight=%0d)", stdp_w);
            $fatal(1);
        end

        // 5. Teste STDP: saturacao LTD (sem underflow)
        for (i = 0; i < 80; i = i + 1) begin
            @(negedge clk); stdp_pre = 0; stdp_post = 1;
            @(posedge clk);
            @(negedge clk); stdp_pre = 1; stdp_post = 0;
            @(posedge clk);
            @(negedge clk); stdp_pre = 0; stdp_post = 0;
            repeat (6) @(posedge clk);
        end
        #1;
        if (stdp_w > 8'd127) begin
            $display("ERRO: STDP LTD sofreu underflow (weight=%0d)", stdp_w);
            $fatal(1);
        end

        // 6. Teste Multilayer: propagacao L1 -> L2
        for (i = 0; i < 60; i = i + 1) begin
            @(negedge clk);
            ml_in = 2'b11;
            @(posedge clk); #1;
            if (ml_hidden != 4'b0000) l1_count = l1_count + 1;
            if (ml_out    != 4'b0000) l2_count = l2_count + 1;
        end
        if (l1_count == 0 || l2_count == 0) begin
            $display("ERRO: Multilayer sem propagacao (L1=%0d, L2=%0d)", l1_count, l2_count);
            $fatal(1);
        end

        $display("PASS: Todos os testes de corner cases passaram! (L1_spikes=%0d, L2_spikes=%0d, final_W=%0d)",
                 l1_count, l2_count, stdp_w);
        $finish;
    end

endmodule
