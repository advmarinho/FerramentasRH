package com.treinamento.rpa;

import jakarta.persistence.*;
import lombok.*;

import java.time.LocalDate;
import java.time.LocalDateTime;

@Entity
@Data
@NoArgsConstructor
@AllArgsConstructor
public class Participante {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, length = 50)
    private String reCpf;

    @Column(nullable = false, length = 255)
    private String nome;

    @Column(length = 255)
    private String setorProcesso;

    @Lob
    @Column(columnDefinition = "LONGTEXT")  // Isso é opcional, mas especifica que estamos usando LONGTEXT
    private String rubrica;

    @Column(nullable = false)
    private boolean assinaturaValida;

    private LocalDateTime dataHoraAssinatura;

    @Column(length = 255)
    private String eventoInterno;

    @Column(length = 255)
    private String eventoExterno;

    @Column(length = 255)
    private String nomeTreinamento;

    @Column(length = 255)
    private String nomeInstrutor;

    private LocalDate dataTreinamento;

    @Column(length = 50)
    private String cargaHoraria;

    @Column(length = 255)
    private String local;
}
