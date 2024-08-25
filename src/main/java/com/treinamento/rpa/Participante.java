package com.treinamento.rpa;

import jakarta.persistence.*;
import lombok.*;

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
    private String rubrica;

    @Column(nullable = false)
    private boolean assinaturaValida;

    private LocalDateTime dataHoraAssinatura;
}
