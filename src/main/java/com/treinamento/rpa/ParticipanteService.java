package com.treinamento.rpa;

import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Optional;

@Service
@RequiredArgsConstructor
public class ParticipanteService {

    private final ParticipanteRepository participanteRepository;

    public List<Participante> listarTodos() {
        return participanteRepository.findAll();
    }

    public Optional<Participante> buscarPorId(Long id) {
        return participanteRepository.findById(id);
    }

    public Participante salvar(Participante participante) {
        return participanteRepository.save(participante);
    }

    public Participante atualizar(Long id, Participante participanteAtualizado) {
        return participanteRepository.findById(id)
                .map(participante -> {
                    participante.setReCpf(participanteAtualizado.getReCpf());
                    participante.setNome(participanteAtualizado.getNome());
                    participante.setSetorProcesso(participanteAtualizado.getSetorProcesso());
                    participante.setRubrica(participanteAtualizado.getRubrica());
                    participante.setAssinaturaValida(participanteAtualizado.isAssinaturaValida());
                    participante.setDataHoraAssinatura(participanteAtualizado.getDataHoraAssinatura());
                    return participanteRepository.save(participante);
                })
                .orElseThrow(() -> new RuntimeException("Participante não encontrado com o ID: " + id));
    }

    public void excluir(Long id) {
        participanteRepository.deleteById(id);
    }
}
